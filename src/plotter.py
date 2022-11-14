from argparse import ArgumentParser
import json
from time import time
from matplotlib import pyplot as plt
from pathlib import Path
import pandas as pd
import requests

from rich import print as rprint
from rich.table import Table
from rich.console import Console

LIMIT_MAX = 100

CACHE_PATH = Path('cache')

BEST_COLOR = (0, 255, 0)
WORST_COLOR = (255, 0, 0)

def get_gradient(lowest, highest, value):
  # higher ratio means closer to highest point
  ratio = (value - lowest) / (highest - lowest)

  result = [int(w * (1 - ratio) + b * ratio) for (w, b) in zip(WORST_COLOR, BEST_COLOR)]
  
  return f"rgb({result[0]},{result[1]},{result[2]})"

# scores are ordered from earliest to newest
def get_data_from_scoresaber(player_id: str, force_fetch: bool = False):
  RECENT_FILENAME = CACHE_PATH / f'latest_{player_id}.json'
  now_time = time()
  if not force_fetch and RECENT_FILENAME.exists():
    with open(str(RECENT_FILENAME)) as f:
      data = json.load(f)
      # not older than a day
      if now_time - data['timestamp'] <= 60 * 60 * 24:
        return data

  scores = []
  page = 1
  REQUEST_URL = f"https://scoresaber.com/api/player/{player_id}/scores?limit={LIMIT_MAX}&sort=recent&withMetadata=false"
  while True:
    url = REQUEST_URL + f"&page={page}"
    print('Requesting', url)
    res = requests.get(url)
    # all pages exhausted
    if res.status_code != 200:
      print("Exiting at", res.json())
      break
    
    data_got = res.json()
    scores_curr = data_got["playerScores"]
    if len(scores_curr) == 0:
        print("Exited at empty list")
        break
    scores.extend(scores_curr)
    page += 1
  
  scores.reverse()
  final_data = { "timestamp": now_time, "scores": scores }
  with open(str(RECENT_FILENAME), 'w') as f:
    json.dump(final_data, f)
  return final_data

def get_all_scores(player_id: str, force_fetch: bool=False, filter_fn=None):
  data = get_data_from_scoresaber(player_id, force_fetch)
  # certain songs have a zero maxScore, possibly they are unranked
  # so we filter them out
  scores = list(filter(filter_fn, filter(lambda x: x['leaderboard']['maxScore'], data['scores'])))
  return scores
  
def plot_time_chart(values, color='red'):
  plt.plot(values, color=color)
  plt.show()

def get_raw_pp(scores):
  return list(map(lambda x: x['score']['pp'], scores))

def get_weighted_pp(scores):
  return list(map(lambda x: x['score']['pp'] * x['score']['weight'], scores))

def get_stars(scores):
  return list(map(get_star_one_score, scores))

def get_star_one_score(score_obj):
  return score_obj['leaderboard']['stars']

def get_acc_one_score(score_obj):
  return int(10000 * score_obj['score']['modifiedScore'] / score_obj['leaderboard']['maxScore']) / 100

def get_accuracy(scores):
  return list(map(get_acc_one_score, scores))

def get_name_one_score(score_obj):
  full_name = score_obj['leaderboard']['songName'] + ' - ' + score_obj['leaderboard']['songAuthorName']
  name = full_name
  if len(full_name) > 50:
    name = full_name[:50] + '...'
  return name

def get_names(scores):
  return list(map(get_name_one_score, scores))

def plot_pp(scores):
  plot_time_chart(get_raw_pp(scores), color='blue')
  plot_time_chart(get_weighted_pp(scores), color='green')

def plot_stars_matrix(scores):
  stars = get_stars(scores)
  accuracy = get_accuracy(scores)
  names = get_names(scores)
  raw_pp = get_raw_pp(scores)
  highest_acc = max(accuracy)
  lowest_acc = min(accuracy)
  # highest_pp = max(raw_pp)
  # lowest_pp = min(raw_pp)

  # zip data
  data = list(zip(stars, accuracy, names, raw_pp))

  # sort list by star rating
  data = sorted(data)

  # print for check
  def get_print_string(x):
    # color = get_gradient(lowest_pp, highest_pp, x[3])
    # formatted_pp = f"[{color}]{x[3]}[/]"
    color_acc = get_gradient(lowest_acc, highest_acc, x[1])
    formatted_accuracy = f"[{color_acc}]{x[1]}[/]"
    return f"{x[0]}, {formatted_accuracy}, {x[3]}, {x[2]}"

  rprint('\n'.join(map(get_print_string, data)))

  accSeries = pd.Series(accuracy, name="Accuracies")
  print(accSeries.describe())
  
  # unzip and plot

  # stars, accuracy, names, raw_pp = zip(*data)
  # plt.plot(stars, accuracy, color='red')
  # plt.show()

def plot_comparison(scores, scores_player, name_player):
  # tuples of (my score, their score, difference, song name)
  diff_list = []
  for score in scores:
    songhash = score['leaderboard']['songHash']
    comparable = None
    for score_2 in scores_player:
      if score_2['leaderboard']['songHash'] == songhash:
        comparable = score_2
        break
    if comparable:
      data = (get_acc_one_score(score), get_acc_one_score(comparable), get_star_one_score(score), get_name_one_score(score))
      diff_list.append(data)
  diff_list.sort(key=lambda x:x[2])
  table = Table(title="Score comparison")
  table.add_column('My score')
  table.add_column('Their score')
  table.add_column('Difficulty')
  table.add_column('Song name')

  score_diff_list = list(map(lambda x: x[0] - x[1], diff_list))
  highest_diff = max(score_diff_list)
  lowest_diff = min(score_diff_list)

  for (s1, s2, star, name) in diff_list:
    color_acc = get_gradient(lowest_diff, highest_diff, s1 - s2)
    formatted_s1 = f"[{color_acc}]{s1}[/]"
    table.add_row(formatted_s1, str(s2), str(star), name)

  console = Console()
  console.print(table)


if __name__ == "__main__":
  parser = ArgumentParser("ScoreSaber scorer")
  parser.add_argument('--force', action='store_true', help='Force refetch data from ScoreSaber')
  parser.add_argument('--compare', action='store_true', help='Compare myself against given player')
  parser.add_argument('--player', action='store', help='Fetch based on username')
  args = parser.parse_args()

  # codergamer
  player_id = "76561199212289731"
  other_player_id = None

  if args.player is not None:
    mapping = {
      'AK': '76561197988817968'
    }
    if args.compare:
      other_player_id = mapping[args.player]
    else:
      player_id = mapping[args.player]

  # any song less than 5 star is not helping me get 200pp
  # highest I have so far on a 4star song is 180pp on a 93% play
  # so now I should switch to >= 5 star songs
  # filter out low star songs
  filter_fn = lambda x: x['leaderboard']['stars'] >= 5

  scores = get_all_scores(player_id, args.force, filter_fn)
  if other_player_id:
    scores_other = get_all_scores(other_player_id, args.force, filter_fn)
  
  if args.compare:
    plot_comparison(scores, scores_other, args.player)
  else:
    plot_stars_matrix(scores)
