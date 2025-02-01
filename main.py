import os
import requests
import random
import schedule
import time
from datetime import datetime, timedelta

TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')
WEATHER_API_KEY = os.environ.get('WEATHER_API_KEY')
CITY = os.environ.get('CITY')
UNITS = os.environ.get('UNITS')
DAILY_POST_TIME = os.environ.get('DAILY_POST_TIME', "08:00")


def get_weather():
    """
    Retrieve current weather for the specified city using OpenWeatherMap API.
    Returns a string summarizing the weather or an error message.
    """
    weather_url = "https://api.openweathermap.org/data/2.5/weather"
    params = {
        "q": CITY,
        "appid": WEATHER_API_KEY,
        "units": UNITS
    }

    try:
        response = requests.get(weather_url, params=params)
        data = response.json()

        if response.status_code != 200:
            return f"Error retrieving weather: {data.get('message', 'Unknown error')}"

        weather_description = data['weather'][0]['description'].capitalize()
        temperature = data['main']['temp']

        weather_summary = (f"Here in {CITY} is {weather_description} morning, "
                           f"gentle breeze blowing, "
                           f"{temperature}°C")
        return weather_summary

    except Exception as e:
        return f"Exception during weather retrieval: {str(e)}"


def get_afternoon_forecast():
    url = "https://api.openweathermap.org/data/2.5/forecast"
    params = {
        "q": CITY,
        "appid": WEATHER_API_KEY,
        "units": UNITS
    }

    try:
        response = requests.get(url, params=params)
        data = response.json()

        if "list" not in data:
            return "Could not retrieve forecast data."

        forecast_list = data["list"]
        today_date = datetime.now().strftime("%Y-%m-%d")
        afternoon_forecast = None

        # Try to find today's forecast for 15:00:00
        for forecast in forecast_list:
            dt_txt = forecast.get("dt_txt", "")
            if dt_txt.startswith(today_date) and "15:00:00" in dt_txt:
                afternoon_forecast = forecast
                break

        # If not found for today, try for tomorrow.
        if not afternoon_forecast:
            tomorrow_date = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
            for forecast in forecast_list:
                dt_txt = forecast.get("dt_txt", "")

                if dt_txt.startswith(tomorrow_date) and "15:00:00" in dt_txt:
                    afternoon_forecast = forecast
                    break

        if not afternoon_forecast:
            return "Afternoon forecast not available."

        if "main" not in afternoon_forecast:
            return "Afternoon forecast data incomplete."

        weather_description = afternoon_forecast["weather"][0]["description"].capitalize()
        temperature = afternoon_forecast["main"]["temp"]
        forecast_message = (
            f"This afternoon it will be going up to {temperature}°C")
        return forecast_message

    except Exception as e:
        return f"Error retrieving forecast: {e}"


def send_telegram_message(message):
    bot_token = os.environ.get('TELEGRAM_BOT_TOKEN')
    if not bot_token:
        print("TELEGRAM_BOT_TOKEN is not set!")
    else:
        print("Bot token loaded successfully.")
    telegram_api_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
    }

    response = requests.post(telegram_api_url, data=payload)
    if response.status_code != 200:
        print("Error sending message:", response.text)
    else:
        print("Message sent successfully!")


def send_today_weather():
    """
    Sends a sequence of messages to the Telegram channel including a greeting,
    today's date (with a special message on Fridays), the current weather, and a well-wish.
    """
    today = datetime.now()
    date_str = today.strftime("%B %d, %Y")  # Format: "December 16, 2022"
    day_name = today.strftime("%A")  # Full weekday name, e.g., "Monday"

    send_telegram_message("Good morning")
    time.sleep(3)  # Short delay between messages

    if day_name == 'Friday':
        send_telegram_message(f'''It's {date_str}\n
        and if YOU CAN BELIEVE IT - IT'S A FRIDAY ONCE AGAIN!!!''')
        time.sleep(3)
    else:
        send_telegram_message(f"It's {date_str} and it's a {day_name}")
        time.sleep(3)

    weather_info = get_weather()
    send_telegram_message(weather_info)
    time.sleep(3)

    weather_info = get_afternoon_forecast()
    send_telegram_message(weather_info)
    time.sleep(3)

    send_telegram_message("And it looks like we're going to be enjoying beautiful blue skies and golden sunshine all along the way!")
    time.sleep(4)

    send_telegram_message("Everyone, Have a great day!")
    time.sleep(2)


def send_today_number():
    """
    Sends a sequence of messages to the Telegram channel for the number of the day
    """
    today = datetime.now()
    date_str = today.strftime("%B %d, %Y")  # Format: "December 16, 2022"

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

    send_telegram_message(f"Today's number is...")
    time.sleep(4)

    random_number = random.randint(1, 10)
    send_telegram_message(f"{random_number}!")
    time.sleep(2)


# def job():
#     """
#     The scheduled job that sends the series of messages.
#     """
#     print(f"Running job at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
#     send_today_weather()
#     send_today_number()


# def main():
#     # Schedule the job to run every day at the specified time.
#     schedule.every().day.at(DAILY_POST_TIME).do(job)
#     print(f"Scheduled daily messages at {DAILY_POST_TIME}.")
#
#     # Run the scheduler continuously.
#     while True:
#         schedule.run_pending()
#         time.sleep(30)  # Check every 30 seconds


if __name__ == "__main__":
    send_today_weather()
    send_today_number()
    # main()
