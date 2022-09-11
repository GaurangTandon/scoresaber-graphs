import json
from time import time
from matplotlib import pyplot as plt
from pathlib import Path
import requests

PLAYER_ID = "76561199212289731"
LIMIT_MAX = 100
REQUEST_URL = f"https://scoresaber.com/api/player/{PLAYER_ID}/scores?limit={LIMIT_MAX}&sort=recent&withMetadata=false"

CACHE_PATH = Path('cache')
RECENT_FILENAME = CACHE_PATH / 'latest.json'

# scores are ordered from earliest to newest
def get_all_scores():
  now_time = time()
  if RECENT_FILENAME.exists():
    with open(str(RECENT_FILENAME)) as f:
      data = json.load(f)
      # not older than a day
      if now_time - data['timestamp'] <= 60 * 60 * 24:
        return data["scores"]

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
  return final_data["scores"]

def plot_time_chart(values, color='red'):
  plt.plot(values, color=color)
  plt.show()

def plot_pp(scores):
  raw_pp = list(map(lambda x: x['score']['pp'], scores))
  weighted_pp = list(map(lambda x: x['score']['pp'] * x['score']['weight'], scores))
  plot_time_chart(raw_pp, color='blue')
  plot_time_chart(weighted_pp, color='green')

if __name__ == "__main__":
  scores = get_all_scores()
  plot_pp(scores)