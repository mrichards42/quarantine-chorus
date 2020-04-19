# Quarantine Chorus

Quarantine Chorus website and serverless backend.

## Requirements

* A [Google Cloud][google-cloud] account
* A [Netlify][netlify] account
* [gcloud][gcloud-cli] cli
* [terraform][terraform]
* python3

## Repo Layout

Directory                              | Description
---------                              | -----------
[web](web)                             | Website
[functions](functions)                 | Google Cloud functions
[infrastructure](infrastructure)       | Terraform files

## Deploying

Deployment is triggered for every push to master.

Functions are deployed using a [Github action](.github/workflows/deploy.yml).

The website is deployed to Netlify at <https://quarantine-chorus.netlify.app/>.

## Data flow overview

See [doc/architecture.svg](doc/architecture.svg) for a diagram.

1. Submission upload
   * User submits metadata
   * Metadata is stored in firestore (a NoSQL database)
   * Backend returns a one-time upload url
   * File is uploaded to cloud storage
2. Audio pipeline (triggered by cloud storage upload)
   * Audio is extracted and compressed
   * Audio is aligned with reference files (TODO)
   * Alignment data is written to firestore (TODO)
3. Video pipeline (TODO)
   * Original upload is resized and aligned using data from the audio pipeline
   * Videos are combined into a final product
     * Better to do video by part, or everyone in a single video? Probably
       depends on how many submissions there are

[google-cloud]: https://cloud.google.com/
[gcloud-cli]: https://cloud.google.com/sdk/gcloud/
[terraform]: https://www.terraform.io/
[netlify]: https://www.netlify.com/
