"""Approximation of simulated annealing."""

import random
from collections import defaultdict


# == Strategies ==

def swap(layout):
    # Collect videos by part
    part_videos = defaultdict(list)
    for v in layout.videos:
        part_videos[v.part].append(v)
    # Find a part to swap
    choices = [videos for videos in part_videos.values() if len(videos) > 1]
    if choices:
        part_videos = random.choice(choices)
        subj, other = random.sample(part_videos, k=2)
        # Swap them
        left, top = subj.left, subj.top
        subj.move(other.left, other.top)
        other.move(left, top)


MIN_CROP_RATIO = .5


def _crop(subj):
    # max_crop = int(subj.width - MIN_CROP_RATIO * subj.original_width)
    # subj.crop_width(random.randint(0, max_crop))
    # subj.crop_width(max(max_crop, 10))
    subj.crop_width(10)


def _uncrop(subj):
    subj.crop_width(random.randint(-20, -1))
    # subj.width = subj.original_width


def crop_random(layout):
    croppable = [v for v in layout.videos if v.crop_ratio() > MIN_CROP_RATIO]
    if croppable:
        _crop(random.choice(layout.videos))


def crop_largest(layout):
    croppable = [v for v in layout.videos if v.crop_ratio() > MIN_CROP_RATIO]
    if croppable:
        _crop(sorted(croppable, key=lambda v: v.width)[-1])


def uncrop_smallest(layout):
    uncroppable = [v for v in layout.videos if v.crop_ratio() < 1]
    if uncroppable:
        _uncrop(sorted(uncroppable, key=lambda v: v.width)[0])


def uncrop_random(layout):
    uncroppable = [v for v in layout.videos if v.crop_ratio() < 1]
    if uncroppable:
        _uncrop(random.choice(uncroppable))


def randomize(layout):
    for v in layout.videos:
        v.move(random.randint(0, 100), random.randint(0, 100))
        # v.width = v.original_width


def add_pillarbox(layout):
    layout.pillarbox_width += 10


def remove_pillarbox(layout):
    layout.pillarbox_width = max(layout.pillarbox_width - 10, 0)


# == Scoring ==

def score_crop(layout):
    max_original_width = max(v.original_width for v in layout.videos)

    def video_score(v):
        crop = (1 - v.crop_ratio())
        expt = 2
        expt *= v.singer_count                         # penalize multiple singers
        expt *= max_original_width / v.original_width  # penalize small videos
        return (100 * crop)**expt

    return sum(video_score(v) for v in layout.videos)


def score_blank(layout):
    return layout.blank_space()


def score_pillarbox(layout):
    # Calculate the actual pillarbox size, not the assigned pillarbox size
    left_box = min(v.left for v in layout.videos)
    right_box = layout.width - max(v.right for v in layout.videos)
    pillarbox_size = (left_box + right_box) * layout.height
    # Give a little credit for the pillarbox. For layouts that are impossible to fit
    # into the chosen aspect ratio, this should at least squeeze the videos a little
    # more tightly.
    # return - pillarbox_size / 3
    return - pillarbox_size / 2


def score_size(layout):
    return layout.width * layout.height


def score(layout):
    badness = (
        0
        # + 10 * score_crop(layout)
        + score_crop(layout)
        # + score_size(layout)
        + score_blank(layout)
        + score_pillarbox(layout)
    )
    return 1 / max(badness, 1)


# == Algorithm ==

_strategies = {
    swap: 10,
    crop_largest: 60,
    crop_random: 50,
    uncrop_smallest: 30,
    uncrop_random: 20,
    randomize: 1,
    add_pillarbox: 5,
    remove_pillarbox: 5,
}

strategies = list(_strategies.keys())
weights = list(_strategies.values())


def pick_strategy():
    return random.choices(strategies, weights)[0]


def step(layout1, threshold=1):
    # Next state
    layout2 = layout1.copy()
    strategy = pick_strategy()
    strategy(layout2)
    layout2.strategy = strategy
    layout2._arrange()
    # Calculate likelihood
    likelihood = score(layout2) / score(layout1)
    if likelihood >= 1:
        return layout2
    elif random.random() <= likelihood * threshold:
        return layout2
    else:
        return layout1


def chain(layout, steps=None, threshold=1):
    i = 0
    while not steps or i < steps:
        yield layout
        # temp = threshold - 2 * (threshold * i) / (steps or 10000)      # linear for first 1/2
        # temp = threshold - 1.333 * (threshold * i) / (steps or 10000)  # linear for first 3/4
        temp = threshold - 1.25 * (threshold * i) / (steps or 10000)  # linear for first 4/5
        # temp = threshold - (threshold * i) / (steps or 10000)          # linear
        # temp = threshold * math.log10((i+1) / (steps or 10000))        # logarithmic
        layout = step(layout, max(0, min(1, temp)))
        i += 1


def best(layout, steps=40000, threshold=1):
    # TODO: there's something to this idea
    # the first pass finds a "pretty good" layout
    # the second pass makes the "pretty good" layout _much_ better
    ls = list(chain(layout, steps, threshold))
    top = random.sample(sorted(ls, key=score)[-100:], k=5)
    # run a few more non-destructive passes
    result = []
    for l in top:
        result.extend(list(chain(l, int(steps/5), threshold=0.001)))
    best2 = max(result, key=score)
    return ls, top, result, best2


def plot_chain(chain, filename=None):
    import matplotlib.pyplot as plt
    import numpy as np
    a = np.array(list(map(score, chain)))
    plt.plot(a)
    if filename:
        plt.savefig(filename)
        plt.close()
    else:
        plt.show()


if __name__ == '__main__':
    import sys
    from pathlib import Path
    sys.path.append(str(Path(__file__).resolve().parent))
    import layout
    filenames = random.sample(sys.argv[1:], len(sys.argv) - 1)
    initial_layout = layout.from_files(filenames)
    chain1, top_initial, chain2, best2 = best(layout.from_files(filenames))
    best1 = top_initial[-1]
    Path('init.svg').write_text(initial_layout.center().to_svg())
    Path('best1.svg').write_text(best1.center().to_svg())
    Path('best2.svg').write_text(best2.center().to_svg())
    plot_chain(chain1, 'chain1.svg')
    plot_chain(chain2, 'chain2.svg')
