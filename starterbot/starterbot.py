import os
import time
import re
import requests
from slackclient import SlackClient
from geotext import GeoText
import difflib

# instantiate Slack client
slack_client = SlackClient(os.environ.get('SLACK_BOT_TOKEN'))
# starterbot's user ID in Slack: value is assigned after the bot starts up
starterbot_id = None

# constants
RTM_READ_DELAY = 1 # 1 second delay between reading from RTM
MENTION_REGEX = "^<@(|[WU].+?)>(.*)"

def get_city_suggestion(city):
    cities = []
    filename ='cities.txt'
    with open(filename, "rt", encoding='UTF8') as f:
        for line in f:
            cities.append(line.split()[0].replace(',', '').strip().title())
    return difflib.get_close_matches(city, cities)

def parse_bot_commands(slack_events):
    """
        Parses a list of events coming from the Slack RTM API to find bot commands.
        If a bot command is found, this function returns a tuple of command and channel.
        If its not found, then this function returns None, None.
    """
    for event in slack_events:
        if event["type"] == "message" and not "subtype" in event:
            user_id, message = parse_direct_mention(event["text"])
            if user_id == starterbot_id:
                return message, event["channel"]
    return None, None


def parse_direct_mention(message_text):
    """
        Finds a direct mention (a mention that is at the beginning) in message text
        and returns the user ID which was mentioned. If there is no direct mention, returns None
    """
    matches = re.search(MENTION_REGEX, message_text)
    # the first group contains the username, the second group contains the remaining message
    return (matches.group(1), matches.group(2).strip()) if matches else (None, None)


def get_celcius(kelvin):
    return kelvin-273.15


def weather_api_call(city_name):
    URL = "http://api.openweathermap.org/data/2.5/weather?q="
    API_KEY = os.environ.get('WEATHER_API_KEY')
    request_string = URL+city_name+API_KEY
    r = requests.get(request_string)
    data_json = r.json()

    temp = round(get_celcius(data_json['main']['temp']), 1)
    humidity = data_json['main']['humidity']
    weather_description = data_json['weather'][0]['description']

    return temp, humidity, weather_description


def handle_command(command, channel):

    if "weather" in command or "Weather" in command:
        command = command.replace("weather", "").strip()
        cities = GeoText(command.title())
        if len(cities.cities) < 1:

            suggestion = get_city_suggestion(command)
            if len(suggestion) > 0:
                temp, humidity, weater_discription = weather_api_call(suggestion[0])
                output = "The weather in {} is {} \nThe temperatute is {} C\n".format(suggestion[0], weater_discription, temp)

                slack_client.api_call(
                    "chat.postMessage",
                    channel=channel,
                    text=output
                )
            else:
                slack_client.api_call(
                    "chat.postMessage",
                    channel=channel,
                    text=command
                )
        else:
            temp, humidity, weater_discription = weather_api_call(cities.cities[0])
            output = "The weather in {} is {} \nThe temperatute is {} C\n".format(cities.cities[0], weater_discription, temp)
            slack_client.api_call(
                "chat.postMessage",
                channel=channel,
                text=output
        )
    else:
        slack_client.api_call(
            "chat.postMessage",
            channel=channel,
            text=command
        )


if __name__ == "__main__":
    if slack_client.rtm_connect(with_team_state=False):
        print("Starter Bot connected and running!")
        # Read bot's user ID by calling Web API method `auth.test`
        starterbot_id = slack_client.api_call("auth.test")["user_id"]
        while True:
            command, channel = parse_bot_commands(slack_client.rtm_read())
            if command:
                handle_command(command, channel)
            time.sleep(RTM_READ_DELAY)
    else:
        print("Connection failed. Exception traceback printed above.")