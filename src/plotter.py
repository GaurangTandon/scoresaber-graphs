from argparse import ArgumentParser
import json
from time import time
from matplotlib import pyplot as plt
from pathlib import Path
import requests

from rich import print as rprint

PLAYER_ID = "76561199212289731"
LIMIT_MAX = 100
REQUEST_URL = f"https://scoresaber.com/api/player/{PLAYER_ID}/scores?limit={LIMIT_MAX}&sort=recent&withMetadata=false"

CACHE_PATH = Path('cache')
RECENT_FILENAME = CACHE_PATH / 'latest.json'

BEST_COLOR = (0, 255, 0)
WORST_COLOR = (255, 0, 0)

def get_gradient(lowest, highest, value):
  # higher ratio means closer to highest point
  ratio = (value - lowest) / (highest - lowest)

  result = [int(w * (1 - ratio) + b * ratio) for (w, b) in zip(WORST_COLOR, BEST_COLOR)]
  
  return f"rgb({result[0]},{result[1]},{result[2]})"

# scores are ordered from earliest to newest
def get_data_from_scoresaber(force_fetch: bool = False):
  now_time = time()
  if not force_fetch and RECENT_FILENAME.exists():
    with open(str(RECENT_FILENAME)) as f:
      data = json.load(f)
      # not older than a day
      if now_time - data['timestamp'] <= 60 * 60 * 24:
        return data

  scores = []
  page = 1
  while True:
    url = REQUEST_URL + f"&page={page}"
    print('Requesting', url)
    res = requests.get(url)
    # all pages exhausted
    if res.status_code != 200:
      print("Exiting at", res.json())
      break
    
    data_got = res.json()
    scores.extend(data_got["playerScores"])
    page += 1
  
  scores.reverse()
  final_data = { "timestamp": now_time, "scores": scores }
  with open(str(RECENT_FILENAME), 'w') as f:
    json.dump(final_data, f)
  return final_data

def get_all_scores(force_fetch: bool=False):
  data = get_data_from_scoresaber(force_fetch)
  # certain songs have a zero maxScore, possibly they are unranked
  # so we filter them out
  scores = list(filter(lambda x: x['leaderboard']['maxScore'], data['scores']))
  return scores

def plot_time_chart(values, color='red'):
  plt.plot(values, color=color)
  plt.show()

def get_raw_pp(scores, filter_fn=lambda x: True):
  return list(map(lambda x: x['score']['pp'], filter(filter_fn, scores)))

def get_weighted_pp(scores, filter_fn=lambda x: True):
  return list(map(lambda x: x['score']['pp'] * x['score']['weight'], filter(filter_fn, scores)))

def get_stars(scores, filter_fn=lambda x: True):
  return list(map(lambda x: x['leaderboard']['stars'], filter(filter_fn, scores)))

def get_accuracy(scores, filter_fn=lambda x: True):
  return list(map(lambda x: int(10000 * x['score']['modifiedScore'] / x['leaderboard']['maxScore']) / 100, filter(filter_fn, scores)))

def get_names(scores, filter_fn=lambda x: True):
  return list(map(lambda x: x['leaderboard']['songName'] + ' - ' + x['leaderboard']['songAuthorName'], filter(filter_fn, scores)))

def plot_pp(scores):
  plot_time_chart(get_raw_pp(scores), color='blue')
  plot_time_chart(get_weighted_pp(scores), color='green')

def plot_stars_matrix(scores):
  filter_fn = lambda x: x['leaderboard']['stars'] >= 4.5
  stars = get_stars(scores, filter_fn)
  accuracy = get_accuracy(scores, filter_fn)
  names = get_names(scores, filter_fn)
  raw_pp = get_raw_pp(scores, filter_fn)
  highest = max(raw_pp)
  lowest = min(raw_pp)
  highest_acc = max(accuracy)
  lowest_acc = min(accuracy)

  # zip and filter out low star songs
  data = list(zip(stars, accuracy, names, raw_pp))

  # sort list by star rating
  data = sorted(data)

  # print for check
  def get_print_string(x):
    # color = get_gradient(lowest, highest, x[3])
    # formatted_pp = f"[{color}]{x[3]}[/]"
    color_acc = get_gradient(lowest_acc, highest_acc, x[1])
    formatted_accuracy = f"[{color_acc}]{x[1]}[/]"
    return f"{x[0]}, {formatted_accuracy}, {x[3]}, {x[2]}"

  rprint('\n'.join(map(get_print_string, data)))
  # unzip and plot

  # stars, accuracy, names, raw_pp = zip(*data)
  # plt.plot(stars, accuracy, color='red')
  # plt.show()

if __name__ == "__main__":
  parser = ArgumentParser("ScoreSaber scorer")
  parser.add_argument('--force', action='store_true', help='Force refetch data from ScoreSaber')
  args = parser.parse_args()

  scores = get_all_scores(args.force)
  # plot_pp(scores)
  plot_stars_matrix(scores)
