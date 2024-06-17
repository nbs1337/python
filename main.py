import requests
import time
from datetime import datetime, timedelta
import logging
import pandas as pd
import os

# Перечень сайтов для мониторинга
sites = [
    "https://www.sberbank.ru",
    "https://www.vtb.ru",
    "https://www.gazprombank.ru",
    "https://www.ingos.ru",
    "https://www.raiffeisen.ru"
]

# Настройка логгирования
log_file = 'site_monitoring.log'
logging.basicConfig(filename=log_file, level=logging.INFO,
                    format='%(asctime)s - %(message)s')


# Проверка доступности сайта
def check_site(url):
    try:
        proxies = {
            "http": None,
            "https": None,
        }
        response = requests.get(url, timeout=10, proxies=proxies, verify=False)
        response.raise_for_status()
        return True
    except requests.exceptions.SSLError as ssl_err:
        return f"SSL Error: {ssl_err}"
    except requests.exceptions.HTTPError as http_err:
        return f"HTTP Error: {http_err}"
    except requests.exceptions.RequestException as req_err:
        return f"Request Error: {req_err}"


# Основная функция мониторинга
def monitor_sites(sites, period_seconds=60):
    site_status = {site: True for site in sites}
    start_time = datetime.now()
    end_time = start_time + timedelta(days=1)
    check_interval = period_seconds / len(sites)

    while datetime.now() < end_time:
        for site in sites:
            print(f"Checking site: {site}")  # Debug information
            status = check_site(site)
            current_time = datetime.now()
            if status is True:
                if not site_status[site]:
                    logging.info(f"{site} - {current_time} - Site restored")
                    print(f"{site} - Site restored")  # Debug information
                site_status[site] = True
            else:
                if site_status[site]:
                    logging.info(f"{site} - {current_time} - {status}")
                    print(f"{site} - {status}")  # Debug information
                site_status[site] = False
            time.sleep(check_interval)


# Формирование отчета
def generate_report(log_file, report_date):
    # Загрузка логов
    logs = []
    if not os.path.exists(log_file):
        print(f"Log file {log_file} does not exist.")
        return pd.DataFrame()

    with open(log_file, 'r') as f:
        for line in f:
            parts = line.strip().split(' - ')
            if len(parts) == 4:
                site, log_time, message = parts[1], parts[0], parts[3]
                logs.append({'time': log_time, 'site': site, 'message': message})

    if not logs:
        print("No logs found.")
        return pd.DataFrame()

    df = pd.DataFrame(logs)
    df['time'] = pd.to_datetime(df['time'])
    report_start = pd.to_datetime(f"{report_date} 00:00:00")
    report_end = pd.to_datetime(f"{report_date} 23:59:59")
    report_df = df[(df['time'] >= report_start) & (df['time'] <= report_end)]

    report_data = []
    for site in sites:
        site_logs = report_df[report_df['site'] == site]
        uptime = 0
        downtime = timedelta()
        last_down_time = None

        for _, row in site_logs.iterrows():
            if 'Site restored' in row['message']:
                if last_down_time:
                    downtime += row['time'] - last_down_time
                    last_down_time = None
            else:
                last_down_time = row['time']

        if last_down_time:
            downtime += report_end - last_down_time

        uptime = (timedelta(days=1) - downtime).total_seconds() / timedelta(days=1).total_seconds() * 100
        report_data.append({
            'site': site,
            'uptime': f"{uptime:.2f}%",
            'downtime': str(downtime)
        })

    report_df = pd.DataFrame(report_data)
    report_df.columns = ['Наименование организации', 'Uptime, %', 'Общее время недоступности сайта за период']

    return report_df


# Запуск мониторинга
monitor_sites(sites)

# Генерация отчета
report_date = datetime.now().strftime('%Y-%m-%d')  # Текущая дата
report = generate_report(log_file, report_date)

if not report.empty:
    print(report)

    # Сохранение отчета
    report_file = f'site_availability_report_{report_date}.csv'
    report.to_csv(report_file, index=False)
    print(f"Отчет сохранен в {report_file}")  # Дополнительное сообщение

    # Вывод пути к логам и отчету
    print(f"Путь к логам: {os.path.abspath(log_file)}")
    print(f"Путь к отчету: {os.path.abspath(report_file)}")
else:
    print("Отчет не был сгенерирован.")
