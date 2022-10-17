import os
from datetime import datetime

from h2ox.w2w.reservoirs import refresh_reservoir_levels
from h2ox.w2w.slackbot import SlackMessenger

    
if __name__=="__main__":
    
    today = datetime.now()
    
    token=os.environ.get("SLACKBOT_TOKEN")
    target=os.environ.get("SLACKBOT_TARGET")
    
    if token is not None and target is not None:

        slackmessenger = SlackMessenger(
            token=token,
            target=target,
            name="h2ox-w2w",
        )
    else:
        slackmessenger=None
        
    filled_datapts = refresh_reservoir_levels(today)
    if slackmessenger is not None:
        slackmessenger.message(f"added {filled_datapts} data points")