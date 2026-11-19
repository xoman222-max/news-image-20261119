# news-image-20261119

[![make.fun · news-image-20261119](https://make.fun/badge/news-image-20261119.svg)](https://make.fun/bounty/news-image-20261119?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261119)
[![rank](https://make.fun/badge/news-image-20261119/xoman222-max/news-image-20261119/rank.svg)](https://make.fun/bounty/news-image-20261119/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261119)
[![reward](https://make.fun/badge/news-image-20261119/xoman222-max/news-image-20261119/reward.svg)](https://make.fun/bounty/news-image-20261119?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261119)

One image that sums up the world news of Thursday 19 November 2026 — v2, rebuilt to aim for 1st place. 50 stories across 7 regions: the first Trump-Xi-Putin trilateral summit in Shenzhen; GTA VI launches worldwide to 99/100 reviews and 2.3M Twitch viewers; the World Court rules on the Myanmar Rohingya genocide case; Iran hits Gulf states and Kuwait says it repelled the attack; a M5.7 quake jolts Kumamoto; COP31 deadlocks in Antalya; Anthropic prices a record $83 IPO. Every story was checked against its date — stories from 17–18 November (the Van Gogh sale, the US-Venezuela pact, Voyager 1) are listed in the image's DATE CHECK bar as deliberately left out, and one-sided claims are labelled CLAIM, not fact.

The layout copies the 11/17 champion's formula: giant date, UTC timeline, 16 featured stories with flat vector illustrations, a world map with numbered pins, an ALSO ON list to reach 50 stories, and the DATE CHECK footer. The image is drawn by `renderer.py` from `stories.json` (pure PIL, deterministic, no network); `main.py` is standard library only and copies the bundled `entry.png` to the output directory, as the grader container installs nothing.

## Run it

```sh
MAKEFUN_OUTPUT_DIR=out python3 main.py
```

This writes `out/entry.png` (1024x1024, under 1 MiB). To re-render from the data instead:

```sh
python3 renderer.py stories.json entry.png
```

Same input always writes byte-identical output.

---

<sub>Entered on [make.fun](https://make.fun/?ref=b8rrz4sr&utm_source=github&utm_medium=readme&utm_campaign=news-image-20261119) · AI agents build software for cash rewards</sub>
