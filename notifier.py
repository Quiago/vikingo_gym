from datetime import datetime, timedelta
import schedule
import time

class Notifier:
    def __init__(self, bot, data_manager):
        self.bot = bot
        self.data_manager = data_manager

    def _check_upcoming_payments(self):
        clients = self.data_manager.get_all_clients()
        today = datetime.now()
        for client in clients:
            user_id, _, _, _, payment_date, _, _, _ = client
            payment_date = datetime.strptime(payment_date, "%d/%m/%Y")
            next_payment_date = payment_date.replace(month=today.month + 1 if today.month < 12 else 1)
            alert_date = next_payment_date - timedelta(days=7)
            if today.date() == alert_date.date():
                self.bot.send_message(user_id, f"Recuerda que tu fecha de pago es el próximo mes el día {payment_date.strftime('%d/%m/%Y')}.")

    def run_scheduler(self):
        schedule.every().day.at("09:00").do(self._check_upcoming_payments)
        while True:
            schedule.run_pending()
            time.sleep(1)
