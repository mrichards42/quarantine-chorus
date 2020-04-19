(function() {
  // === Utils ================================================================
  var KB = 1024;
  var MB = KB * KB;
  var MIN_CHUNK = 256 * KB; // According to google

  function humanFileSize(number, fixedDigits) {
    fixedDigits = fixedDigits || 0;
    if (number < KB) {
      return number + 'bytes';
    } else if (number >= KB && number < MB) {
      return (number / KB).toFixed(fixedDigits) + 'KB';
    } else if (number >= MB) {
      return (number / MB).toFixed(fixedDigits) + 'MB';
    }
  }

  function randInt(min, max) {
    if (!max) {
      return randInt(0, min);
    } else {
      // From https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Math/random#Getting_a_random_integer_between_two_values_inclusive
      return Math.floor(Math.random() * (max - min + 1)) + min;
    }
  }

  function wait(ms) {
    // From https://developer.mozilla.org/en-US/docs/Web/JavaScript/Guide/Using_promises#Creating_a_Promise_around_an_old_callback_API
    return new Promise(function(resolve) {
      setTimeout(resolve, ms)
    });
  }

  function sum(a) {
    return a.reduce(function (x, y) { return x + y }, 0);
  }

  function estimator(movingAveragePoints) {
    movingAveragePoints = movingAveragePoints || 5;
    return {
      points: [],
      _time: function(time) {
        return time == null ? new Date().getTime() : time;
      },
      lap: function(val, time) {
        var last = this.points.slice(-1)[0];
        time = this._time(time);
        this.points.push({
          val: val,
          time: time,
          rate: last ? (val - last.val) / (time - last.time) : null
        });
        return this;
      },
      start: function(time) {
        return this.lap(0, time);
      },
      estimate: function(time) {
        time = this._time(time);
        if (this.points.length > 1) {
          var last = this.points.slice(-1)[0];
          // weighted average
          var rates = this.points.slice(-movingAveragePoints)
            .map(function (p, i) { return p.rate * i});
          var avgRate = sum(rates) / sum(rates.map(function(_, i) { return i }));
          return last.val + avgRate * (time - last.time);
        }
      },
    }
  }

  // === Singers ==============================================================
  var singersContainer = document.getElementById('singersContainer');
  var addSingerBtn = document.getElementById('addSinger');
  var removeSingerBtn = document.getElementById('removeSinger');
  var singerTemplate = document.getElementById('singer1').cloneNode(true);
  singerTemplate.id = '';

  function addSinger(idx) {
    var newSinger = singerTemplate.cloneNode(true);
    newSinger.id = 'singer' + idx;
    singersContainer.appendChild(newSinger);
  }

  function removeSinger(idx) {
    // don't remove the last singer
    if (idx > 0) {
      singersContainer.removeChild(
        document.getElementsByClassName('singer')[idx]);
    }
  }

  function singerCount() {
    return document.getElementsByClassName('singer').length;
  }

  addSingerBtn.addEventListener('click', function (e) {
    e.preventDefault();
    addSinger(singerCount() + 1);
    removeSingerBtn.disabled = false;
  })
  removeSingerBtn.addEventListener('click', function (e) {
    e.preventDefault();
    removeSinger(singerCount() - 1);
    if (singerCount() == 1) {
      removeSingerBtn.disabled = true;
    }
  })

  // === Upload UI ============================================================
  var uploadInput = document.getElementById('uploadInput');
  var uploadDetails = document.getElementById('uploadDetails');
  var uploadPreview = document.getElementById('uploadPreview');

  function updatePreview() {
    while (uploadPreview.firstChild) {
      uploadPreview.removeChild(uploadPreview.firstChild);
    }

    if (uploadInput.files.length === 1) {
      var file = uploadInput.files[0];
      uploadDetails.textContent = file.name + ' (' + humanFileSize(file.size, 1) + ')';
      if (file.type.substr(0, 5) === 'video') {
        var player = document.createElement('video');
        player.controls = true;
        player.src = URL.createObjectURL(file);
        uploadPreview.appendChild(player);
      } else if (file.type.substr(0, 5) === 'audio') {
        var player = document.createElement('audio');
        player.controls = true;
        player.src = URL.createObjectURL(file);
        uploadPreview.appendChild(player);
      }
    }
  }

  uploadInput.addEventListener('change', updatePreview);

  // == Resumable Upload ======================================================

  function bestChunkSize(start_byte, totalSize) {
    // Larger chunks go significantly faster, so this is a tradeoff between
    // making the upload as fast as possible and giving the user some
    // indication of progress.
    if (totalSize < 2 * MB) {
      return MIN_CHUNK;
    } else if (totalSize < 10 * MB) {
      return MB
    // } else if (start_byte < 10 * MB) {
    //   return 2 * MB; // quick initial feedback
    } else if (totalSize < 100 * MB) {
      return 4 * MB
    } else {
      // around 25 chunks
      return Math.floor(totalSize / MB / 25) * MB;
    }
  }

  function uploadChunkRequest(url, file, start_byte) {
    var chunkSize = bestChunkSize(start_byte, file.size);
    var chunk = file.slice(start_byte, start_byte + chunkSize);
    var end_byte = start_byte + chunk.size - 1;
    var byte_range = start_byte + '-' + end_byte + '/' + file.size;
    return fetch(url, {
      method: 'PUT',
      headers: {
        'Content-Type': file.type,
        'Content-Length': chunk.size,
        'Content-Range': 'bytes ' + byte_range,
      },
      body: chunk,
    });
  }

  function nextBackoff(tries, config) {
    var randMs = randInt(1000);
    var backoff = Math.pow(2, (tries - 1)) * (config.backoff || 1000) + randMs;
    return Math.min(backoff, (config.max_backoff || 30000));
  }

  function initUpload(url, file) {
    var RETRY = {
      max_tries: 30,
      backoff: 1000,
    }
    var RETRY_308 = {
      max_tries: 1,
      backoff: 2000,
    }
    var tries = 0;
    var tries308 = 0;

    function resumeRequest() {
      // Attempt to resume from wherever we left off
      // https://cloud.google.com/storage/docs/performing-resumable-uploads#resume-upload
      return fetch(url, {
        method: 'PUT',
        headers: {
          'Content-Range': '*.' + file.size,
        }
      });
    }

    function handleResponse(res) {
      switch (res.status) {
        case 200:
        case 201:
          // File was created: we're done
          return res.json().then(function(data) {
            return {
              done: true,
              response: res,
              data: data,
            }
          });
        case 308:
          tries = 0;
          var match = /bytes=\d+-(\d+)/.exec(res.headers.get('Range'));
          if (match) {
            // Chunk suceeeded: submit the next chunk
            tries308 = 0;
            var last_byte = parseInt(match[1]);
            return {
              progress: last_byte,
              response: res,
              next: function() {
                return uploadChunkRequest(url, file, last_byte + 1).then(handleResponse);
              }
            }
          } else if (tries308 < RETRY_308.max_tries) {
            // Bad range header: ask again after a delay
            // https://cloud.google.com/storage/docs/resumable-uploads#optional_optimization
            console.log('Unable to parse Range header; attempting to resume')
            tries308++;
            var backoff = nextBackoff(tries308, RETRY_308);
            return {
              retriable: true,
              response: res,
              backoff: backoff,
              next: function() {
                return wait(backoff).then(resumeRequest).then(handleResponse);
              }
            }
          }
          // Out of 308 retries; fallthrough to 404 and start again
        case 404:
          if (tries < RETRY.max_tries) {
            // Google doesn't know about this file: start from the beginning
            tries++;
            var backoff = nextBackoff(tries, RETRY);
            return {
              retriable: true,
              progress: 0,
              response: res,
              backoff: backoff,
              next: function() {
                return wait(backoff).then(function() {
                  return uploadChunkRequest(url, file, 0).then(handleResponse);
                })
              }
            }
          } else {
            return {
              error: "Out of retries",
              response: res,
            }
          }
        case 408:
        case 500:
        case 502:
        case 503:
        case 504:
          // Retriable errors
          if (tries < RETRY.max_tries) {
            tries++;
            var backoff = nextBackoff(tries, RETRY);
            return {
              retriable: true,
              response: res,
              next: function() {
                return wait(1000).then(resumeRequest).then(handleResponse);
              }
            }
          } else {
            return {
              error: 'out of retries',
              response: response,
            }
          }
      }
    }

    return uploadChunkRequest(url, file, 0).then(handleResponse);
  }

  // == Submit Form ===========================================================
  var submissionWrapper = document.getElementById('submissionWrapper');
  var submissionForm = document.getElementById('submissionForm');
  submissionForm.reset();
  var submitBtn = document.getElementById('submit');
  var tryAgainBtn = document.getElementById('uploadTryAgain');

  function form2json() {
    function vals(name) {
      var elements = [].slice.call(document.getElementsByName(name));
      return elements.map(function(e) { return e.value });
    }
    function val(name) {
      return vals(name)[0];
    }
    // singers
    var parts = vals('part');
    var names = vals('name');
    var emails = vals('email');
    var singers = parts.map(function(_, i) {
      return {
        part: parts[i],
        name: names[i],
        email: emails[i],
      }
    }).filter(function(singer) {
      return singer.part !== '' || singer.name !== '' || singer.email != ''
    })
    // location
    file = uploadInput.files[0] || {};
    return {
      content_type: file.type,
      content_length: file.size,
      filename: file.name,
      submission: {
        song: val('song'),
        singing: val('singing'),
        singers: singers,
        location: {
          city: val('city'),
          state: val('state'),
          country: val('country'),
        },
      }
    };
  }

  function submissionRequest(data) {
    return fetch('/submission/new', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(data),
    }).then(function(response) {
      return response.json();
    });
  }

  var originalTitle = document.title;

  function performUpload(url, file) {
    var progress = document.getElementById('progress');
    var progressLog = document.getElementById('progressLog');

    progressLog.textContent = 'Starting upload...';

    // moving average estimate
    // var est = estimator().start();
    // var timeout;

    function updateProgress(res) {
      // clearTimeout(timeout);
      if (res.done) {
        progressLog.textContent = 'Done ' + humanFileSize(file.size);
        progress.style.width = '100%';
        document.title = '[100%] ' + originalTitle;
        return;
      } else if (res.progress) {
        var pct = 100 * res.progress / file.size
        progressLog.textContent = 'Upload in progress... '
          + humanFileSize(res.progress) + ' of ' + humanFileSize(file.size)
          + ' (' + pct.toFixed(0) + '%)';
        progress.style.width = pct.toFixed(2) + '%';
        document.title = '[' + pct.toFixed(0) + '%] ' + originalTitle;
        // // calculate a new estimate
        // if (est.estimate()) {
        //   console.log('estimate off by', 100 * (res.progress - est.estimate()) / file.size);
        // }
        // est.lap(res.progress);
      } else if (res.estimate) {
        // // estimate progress
        // var estProgress = est.estimate();
        // if (estProgress) {
        //   estProgress = Math.min(estProgress, file.size);
        //   var pct = 100 * estProgress / file.size;
        //   progressLog.textContent = 'Upload in progress... '
        //     + humanFileSize(estProgress) + ' of ' + humanFileSize(file.size, 0)
        //     + ' (' + pct.toFixed(0) + '%)';
        //   progress.style.width = pct.toFixed(2) + '%';
        //   document.title = '[' + pct.toFixed(0) + '%] ' + originalTitle;
        // }
      }
      // // update the estimate at least every half second
      // timeout = setTimeout(function () {
      //   updateProgress({estimate: true})
      // }, 500);
    }

    function handleResponse(res) {
      console.log(new Date(), 'Upload response', res)
      updateProgress(res)
      if (res.next) {
        return res.next().then(handleResponse);
      } else {
        return res
      }
    }
    return initUpload(url, file).then(handleResponse);
  }

  function submit(formData, file) {

    Sentry.configureScope(function(scope) {
      scope.setExtra("form_data", JSON.stringify(formData));
    });

    // setup the ui
    var progressPanel = document.getElementById('uploadProgress');
    var progressTitle = document.getElementById('progressTitle');
    var progressSubtitle = document.getElementById('progressSubtitle');
    submissionWrapper.setAttribute('aria-hidden', true);
    submissionWrapper.style.display = 'none';
    tryAgainBtn.style.display = 'none';
    progressPanel.setAttribute('aria-hidden', false);
    progressPanel.style.display = 'block';
    var start = new Date();
    console.log('start', start);

    progressTitle.textContent = 'Uploading your submission';
    progressSubtitle.textContent = 'Please leave this window open until your upload is complete';

    return submissionRequest(formData)
      .then(function (response) {
        if (response.upload_url) {
          return performUpload(response.upload_url, file);
        } else {
          throw new Error('bad response', response);
        }
      }).then(function (response) {
        console.log('UPLOAD COMPLETE', response);
        var end = new Date();
        console.log('end', end);
        console.log('elapsed', end - start);
        progressTitle.textContent = 'Upload complete!';
        progressSubtitle.textContent = 'Thank you for your submission.';
      }).catch(function (e) {
        Sentry.captureException(e);
        progressTitle.textContent = 'Something went wrong!';
        if (e.message === 'bad response') {
          console.error('SUBMIT ERROR', e);
          progressSubtitle.textContent = 'Sorry, an error occurred while processing your submission. Please try again.'
        } else {
          console.error('UPLOAD EXCEPTION', e);
          progressSubtitle.textContent = 'Sorry, an error occurred while uploading your file. Please try again.'
        }
        tryAgainBtn.style.display = 'block';
      });
  }

  submitBtn.addEventListener('click', function(e) {
    e.preventDefault();
    submissionForm.className = 'submitted';

    if (submissionForm.reportValidity()) {
      var data = form2json();
      var file = uploadInput.files[0];
      submit(data, file);
    }
  })

  tryAgainBtn.addEventListener('click', function(e) {
    e.preventDefault();
    // assume the form is correct
    var data = form2json();
    var file = uploadInput.files[0];
    submit(data, file);
  })
})()
