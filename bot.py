import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton
import toml
from data_manager import DataManager
from notifier import Notifier
import logging
import threading
from datetime import datetime, timedelta

# Configuración del logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class GymBot:
    def __init__(self):
        self.config = toml.load("config.toml")
        self.TELEGRAM_API_TOKEN = self.config["keys"]["telegram"]
        self.bot = telebot.TeleBot(self.TELEGRAM_API_TOKEN)
        self.data_manager = DataManager()
        self.notifier = Notifier(self.bot, self.data_manager)
        self._setup_handlers()

    def _setup_handlers(self):
        @self.bot.message_handler(commands=['start'])
        def send_welcome(message):
            self._handle_start(message)

        @self.bot.message_handler(commands=['clientes'])
        def handle_client_profiles(message):
            self._handle_client_profiles(message)

        @self.bot.message_handler(commands=['asignar_rol'])
        def assign_role(message):
            self._handle_assign_role(message)

        @self.bot.message_handler(commands=['info_mensualidad'])
        def info_mensualidad(message):
            self._handle_info_mensualidad(message)

        # Otros comandos como pagar_mensualidad, info_mensualidad, mi_progreso, etc.
    def _is_trainer(self):
        if self.current_profile['role'] == 'entrenador':
            return True
        else:
            return False

    def _handle_start(self, message):
        user_id = message.from_user.id
        user_profile = self.data_manager.get_user_profile(user_id)
        if user_profile:
            self.bot.send_message(user_id, "¡Bienvenido de nuevo! Usa el menú para acceder a las opciones.")
            self._show_menu(user_id)
        else:
            self.bot.send_message(user_id, "¡Bienvenido! Vamos a crear tu perfil. ¿Cuál es tu nombre?")
            self.bot.register_next_step_handler(message, self._process_name_step)

    def _process_name_trainer_step(self, message):
        user_id = message.from_user.id
        self.current_profile['role'] = 'entrenador'
        self.current_profile['name'] = message.text
        self.bot.send_message(user_id, "Por favor, ingresa tu primer apellido:")
        self.bot.register_next_step_handler(message, self._process_surname_step)

    def _process_name_step(self, message):
        user_id = message.from_user.id
        self.current_profile = {'user_id': user_id, 'name': message.text}

        # Asignación de rol, aquí puedes usar cualquier lógica para determinar si es un entrenador
        if "Entrenador" in self.current_profile['name']:  # Puedes usar una lista o algún criterio adicional
            self.bot.send_message(user_id, "¡Bienvenido entrenador! ¿Cuál es tu nombre?")
            self.bot.register_next_step_handler(message, self._process_name_trainer_step)
            
        else:
            self.current_profile['role'] = 'cliente'
            self.bot.send_message(user_id, "Por favor, ingresa tu primer apellido:")
            self.bot.register_next_step_handler(message, self._process_surname_step)

    def _process_surname_step(self, message):
        self.current_profile['surname'] = message.text
        self.bot.send_message(self.current_profile['user_id'], "Por favor, ingresa tu carnet de identidad (CI):")
        self.bot.register_next_step_handler(message, self._process_ci_step)

    def _process_ci_step(self, message):
        ci = message.text
        if ci.isdigit() and len(ci) == 11:
            self.current_profile['ci'] = ci
            #self.bot.send_message(self.current_profile['user_id'], "Por favor, ingresa tu fecha de pago de la mensualidad (DD/MM/AAAA):")
            self.bot.send_message(self.current_profile['user_id'], "Ingresa tu peso actual en kg (por ejemplo, 70.5):")
            self.bot.register_next_step_handler(message, self._process_weight_step)
        else:
            self.bot.send_message(self.current_profile['user_id'], "CI no válido. Debe contener 11 dígitos numéricos. Inténtalo de nuevo:")
            self.bot.register_next_step_handler(message, self._process_ci_step)

    def _process_weight_step(self, message):
        try:
            weight = float(message.text)
            if weight > 0:
                self.current_profile['weight'] = weight
                self.bot.send_message(self.current_profile['user_id'], "Ingresa tu estatura en cm (por ejemplo, 175.5):")
                self.bot.register_next_step_handler(message, self._process_height_step)
            else:
                logger.error('Fallo en este proceso")')
        except ValueError:
            self.bot.send_message(self.current_profile['user_id'], "Entrada no válida. Por favor, ingresa tu peso en kg:")
            self.bot.register_next_step_handler(message, self._process_weight_step)

    def _process_height_step(self, message):
        try:
            height = float(message.text)
            if height > 0:
                self.current_profile['height'] = height
                self._show_modality_options(self.current_profile['user_id'])
            else:
                logger.error("Error: La altura ingresada no es válida (debe ser mayor a 0).")
                self.bot.send_message(self.current_profile['user_id'], "La estatura debe ser mayor a 0. Por favor, inténtalo de nuevo:")
                self.bot.register_next_step_handler(message, self._process_height_step)
        except ValueError:
            logger.warning("Error: Entrada no válida para estatura.")
            self.bot.send_message(self.current_profile['user_id'], "Entrada no válida. Por favor, ingresa tu estatura en cm (por ejemplo, 175.5):")
            self.bot.register_next_step_handler(message, self._process_height_step)

    def _show_modality_options(self, user_id):
        # Mostrar opciones de modalidad
        keyboard = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        keyboard.add(KeyboardButton('musculación'))
        keyboard.add(KeyboardButton('crossfit'))
        keyboard.add(KeyboardButton('musculación y crossfit'))
        self.bot.send_message(user_id, "Por favor selecciona tu modalidad:", reply_markup=keyboard)
        # Aquí registramos el próximo paso para capturar la modalidad seleccionada
        self.bot.register_next_step_handler_by_chat_id(user_id, self._process_modality_step)

    def _process_modality_step(self, message):
        modality = message.text.lower()
        valid_modalities = ['musculación', 'crossfit', 'musculación y crossfit']

        if modality in valid_modalities:
            self.current_profile['modality'] = modality
            if self._is_trainer():
                # Guardar perfil de entrenador en la base de datos
                self.current_profile['payment_date'] = None
                self.data_manager.upsert_user_profile(**self.current_profile)
                self.bot.send_message(self.current_profile['user_id'], "Perfil creado exitosamente.")
                self._show_menu(self.current_profile['user_id'])
            else:
                self.bot.send_message(self.current_profile['user_id'], "Por favor, ingresa tu fecha de pago de la mensualidad (DD/MM/AAAA):")
                self.bot.register_next_step_handler(message, self._process_payment_date_step)
        else:
            logger.warning(f"Modalidad inválida seleccionada: {modality}")
            self.bot.send_message(self.current_profile['user_id'], "Modalidad no válida. Por favor selecciona una de las siguientes opciones:")
            # Mostrar opciones de modalidad nuevamente
            self._show_modality_options(self.current_profile['user_id'])

    def _process_payment_date_step(self, message):
        try:
            day, month, year = map(int, message.text.split('/'))
            if 1 <= day <= 31 and 1 <= month <= 12 and year > 1900:
                self.current_profile['payment_date'] = message.text
                self.data_manager.upsert_user_profile(**self.current_profile)  # Guardar en base de datos
                self.bot.send_message(self.current_profile['user_id'], "Perfil creado exitosamente.")
                self._show_menu(self.current_profile['user_id'])
                
            else:
                logger.error('Fallo en este proceso")')
        except ValueError:
            self.bot.send_message(self.current_profile['user_id'], "Formato de fecha no válido. Por favor, ingresa la fecha en formato DD/MM/AAAA:")
            self.bot.register_next_step_handler(message, self._process_payment_date_step)
    




    def _handle_info_mensualidad(self, message):
        user_id = message.from_user.id
        user_profile = self.data_manager.get_user_profile(user_id)
        if user_profile:
            payment_date = datetime.strptime(user_profile[4], '%d/%m/%Y')
            # Calculate days remaining based on payment date
            today = datetime.now()
            payment_this_month = payment_date.replace(year=today.year, month=today.month)
            
            if today.date() >= payment_this_month.date():
                # If we've passed or are on the payment date, look at next month
                if payment_this_month.month == 12:
                    next_payment = payment_this_month.replace(year=payment_this_month.year + 1, month=1)
                else:
                    next_payment = payment_this_month.replace(month=payment_this_month.month + 1)
            else:
                # If payment date hasn't arrived yet, use this month's date
                next_payment = payment_this_month
            
            days_remaining = (next_payment - today).days
            
            self.bot.send_message(user_id, 
                f"Tu próxima fecha de pago es: {next_payment.strftime('%d/%m/%Y')}\n"
                f"Faltan {days_remaining} días para el pago.")
        else:
            self.bot.send_message(user_id, "No se encontró tu perfil. Usa /start para crearlo.")

    def _show_menu(self, user_id):
        user_profile = self.data_manager.get_user_profile(user_id)
        role = user_profile[8]  # Obtén el rol del perfil

        keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
        #keyboard.add(KeyboardButton('/pagar_mensualidad'))
        
        keyboard.add(KeyboardButton('/mi_progreso'))
        keyboard.add(KeyboardButton('/cafeteria'))

        if role == 'cliente':  # Si es un cliente, agrega las opciones extras
            keyboard.add(KeyboardButton('/info_mensualidad'))

        if role == 'entrenador':  # Si es un entrenador, agrega las opciones extras
            keyboard.add(KeyboardButton('/clientes'))  # Ver clientes
            keyboard.add(KeyboardButton('/asignar_rol'))  # Asignar roles

        self.bot.send_message(user_id, "Selecciona una opción del menú:", reply_markup=keyboard)

    def _handle_client_profiles(self, message):
        user_id = message.from_user.id
        user_profile = self.data_manager.get_user_profile(user_id)
        if user_profile and user_profile[8] == 'entrenador':  # Verificar que es entrenador
            clients = self.data_manager.get_all_clients()
            response = "Lista de Clientes:\n\n"
            for client in clients:
                response += f"📋 Nombre: {client[1]} {client[2]}\n"
                response += f"🆔 CI: {client[3]}\n"
                response += f"💰 Fecha de pago: {client[4]}\n"
                response += f"⚖️ Peso: {client[5]}kg\n"
                response += f"📏 Altura: {client[6]}cm\n"
                response += "------------------------\n"
            self.bot.send_message(user_id, response)
        else:
            self.bot.send_message(user_id, "No tienes aun clientes.")

    def _handle_assign_role(self, message):
        user_id = message.from_user.id
        if self.data_manager.get_user_profile(user_id)[8] == 'entrenador':  # Verifica que es un entrenador
            self.bot.send_message(user_id, "Asignando rol...")
            # Lógica para asignar roles aquí
        else:
            self.bot.send_message(user_id, "No tienes permisos para asignar roles.")

    
    def run(self):
        threading.Thread(target=self.notifier.run_scheduler).start()
        try:
            self.bot.polling(none_stop=True, interval=0)
        except Exception as e:
            logger.error(f"Error in polling loop: {str(e)}")
            self.bot.send_message("Admin", f"Bot crashed with error: {str(e)}")