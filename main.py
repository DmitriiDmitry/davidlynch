import os
import requests
import random
import time
from datetime import datetime, timedelta

# Configuration from environment variables.
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')
WEATHER_API_KEY = os.environ.get('WEATHER_API_KEY')
CITY = os.environ.get('CITY')
UNITS = os.environ.get('UNITS', 'metric')


def fetch_data(url, params):
    """
    Helper function to fetch data from a given URL with provided parameters.
    Returns a tuple (data, error) where 'data' is the JSON response (if successful)
    and 'error' is an error message (if any).
    """
    try:
        response = requests.get(url, params=params)
        data = response.json()
        if response.status_code != 200:
            return None, data.get("message", "Unknown error")
        return data, None
    except Exception as e:
        return None, str(e)


def get_weather():
    """
    Retrieve the current weather for the specified city and return a formatted summary.
    """
    weather_url = "https://api.openweathermap.org/data/2.5/weather"
    params = {"q": CITY, "appid": WEATHER_API_KEY, "units": UNITS}
    data, error = fetch_data(weather_url, params)

    if error:
        return f"Error retrieving weather: {error}"

    try:
        weather_description = data['weather'][0]['description'].capitalize()
        temperature = data['main']['temp']
        return (f"Here in {CITY} {weather_description} morning, "
                f"gentle breeze blowing, {temperature}°C")
    except (KeyError, IndexError) as e:
        return f"Incomplete weather data: {e}"


def find_afternoon_forecast(forecast_list, target_date, target_time="15:00:00"):
    """
    Given a list of forecast entries, return the one that matches the target date and time.
    """
    for forecast in forecast_list:
        dt_txt = forecast.get("dt_txt", "")
        if dt_txt.startswith(target_date) and target_time in dt_txt:
            return forecast
    return None


def get_afternoon_forecast():
    """
    Retrieve the forecast data and extract the 15:00 forecast for today or, if unavailable,
    for tomorrow. Returns a formatted message about the expected temperature.
    """
    forecast_url = "https://api.openweathermap.org/data/2.5/forecast"
    params = {"q": CITY, "appid": WEATHER_API_KEY, "units": UNITS}
    data, error = fetch_data(forecast_url, params)

    if error or "list" not in data:
        return f"Error retrieving forecast data: {error or 'No forecast list found'}"

    forecast_list = data["list"]
    today_date = datetime.now().strftime("%Y-%m-%d")
    forecast = find_afternoon_forecast(forecast_list, today_date)

    # If today's forecast at 15:00 isn't available, try tomorrow.
    if not forecast:
        tomorrow_date = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        forecast = find_afternoon_forecast(forecast_list, tomorrow_date)

    if not forecast or "main" not in forecast:
        return "Afternoon forecast not available."

    temperature = forecast["main"]["temp"]
    return f"This afternoon it will be going up to {temperature}°C"


def send_telegram_message(message):
    """
    Send a message to the configured Telegram chat using the Bot API.
    """
    bot_token = TELEGRAM_BOT_TOKEN
    if not bot_token:
        print("TELEGRAM_BOT_TOKEN is not set!")
        return
    else:
        print("Bot token loaded successfully.")

    telegram_api_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "HTML"}
    response = requests.post(telegram_api_url, data=payload)

    if response.status_code != 200:
        print("Error sending message:", response.text)
    else:
        print("Message sent successfully!")


def send_today_weather():
    """
    Sends a series of Telegram messages: a greeting, today's date (with a special message on Fridays),
    the current weather, the afternoon forecast, and a final well-wish.
    """
    today = datetime.now()
    date_str = today.strftime("%B %d, %Y")
    day_name = today.strftime("%A")

    send_telegram_message("Good morning")
    time.sleep(3)

    if day_name == 'Friday':
        send_telegram_message(f"It's {date_str}\nand if YOU CAN BELIEVE IT - IT'S A FRIDAY ONCE AGAIN!!!")
    else:
        send_telegram_message(f"It's {date_str} and it's a {day_name}")
    time.sleep(3)

    send_telegram_message(get_weather())
    time.sleep(3)

    send_telegram_message(get_afternoon_forecast())
    time.sleep(3)

    send_telegram_message(
        "And it looks like we're going to be enjoying beautiful blue skies and golden sunshine all along the way!")
    time.sleep(4)

    send_telegram_message("Everyone, Have a great day!")
    time.sleep(2)


def send_today_number():
    """
    Sends a sequence of messages to the Telegram channel for the "number of the day".
    """
    today = datetime.now()
    date_str = today.strftime("%B %d, %Y")

    send_telegram_message("Here we go for today's number!")
    time.sleep(3)

    send_telegram_message(f"It's {date_str}")
    time.sleep(3)

    send_telegram_message("Ten balls, each ball has a number")
    time.sleep(3)

    send_telegram_message("Numbers one through ten")
    time.sleep(3)

    send_telegram_message("Swirl the numbers")
    time.sleep(3)

    send_telegram_message("Pick a number!")
    time.sleep(3)

    send_telegram_message("Today's number is...")
    time.sleep(4)

    random_number = random.randint(1, 10)
    send_telegram_message(f"{random_number}!")
    time.sleep(2)


if __name__ == "__main__":
    send_today_weather()
    send_today_number()
