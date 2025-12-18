# -------------------------
# IMPORTS
# -------------------------
import os
import time
import random
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib import ticker
from matplotlib.backends.backend_pdf import PdfPages
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.chrome.service import Service

# -------------------------
# Gestión de credenciales
# -------------------------
def save_credentials(username, password):
    with open('credentials.txt', 'w') as file:
        file.write(f"{username}\n{password}")

def load_credentials():
    if not os.path.exists('credentials.txt'):
        return None
    with open('credentials.txt', 'r') as file:
        lines = file.readlines()
        if len(lines) >= 2:
            return lines[0].strip(), lines[1].strip()
    return None

def prompt_credentials():
    username = input("Enter your Instagram username: ")
    password = input("Enter your Instagram password: ")
    save_credentials(username, password)
    return username, password

# -------------------------
# Simulación de pausa
# -------------------------
def human_delay(a=2.0, b=5.0):
    delay = random.uniform(a, b)
    time.sleep(delay)

# -------------------------
# Función de login
# -------------------------
def login(bot, username, password):
    bot.get('https://www.instagram.com/accounts/login/')
    human_delay(2, 4)

    try:
        element = bot.find_element(By.XPATH, "/html/body/div[4]/div/div/div[3]/div[2]/button")
        element.click()
    except NoSuchElementException:
        print("[Info] - Instagram did not require to accept cookies this time.")

    print("[Info] - Logging in...")

    username_input = WebDriverWait(bot, 10).until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, "input[name='username']"))
    )
    password_input = WebDriverWait(bot, 10).until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, "input[name='password']"))
    )

    username_input.clear()
    username_input.send_keys(username)
    password_input.clear()
    password_input.send_keys(password)

    login_button = WebDriverWait(bot, 5).until(
        EC.element_to_be_clickable(
            (By.XPATH, "//div[@role='button']//span[contains(text(), 'Iniciar sesión') or contains(text(), 'Log in')]")
        )
    )

    login_button.click()
    human_delay(15, 20) # Aumentado un poco para asegurar carga del feed

# -------------------------
# Navegador
# -------------------------
def iniciar_navegador(headless=False):
    service = Service()
    options = webdriver.ChromeOptions()
    if headless:
        options.add_argument("--headless")
    options.add_argument('--no-sandbox')
    options.add_argument("--log-level=3")
    # Emulación móvil
    mobile_emulation = {
        "userAgent": "Mozilla/5.0 (Linux; Android 4.2.1; en-us; Nexus 5 Build/JOP40D) AppleWebKit/535.19 (KHTML, like Gecko) Chrome/90.0.1025.166 Mobile Safari/535.19"}
    options.add_experimental_option("mobileEmulation", mobile_emulation)
    bot = webdriver.Chrome(service=service, options=options)
    bot.set_page_load_timeout(30)
    return bot

# ---------------------------------------------------------------------------
# Función: get_profile_stats (MODIFICADA: AHORA EXTRAE BIO)
# ---------------------------------------------------------------------------
def get_profile_stats(bot, username):
    """Extrae seguidores, seguidos, privacidad y BIOGRAFÍA."""
    try:
        bot.get(f"https://www.instagram.com/{username}/")
        human_delay(2, 4)

        num_followers = num_following = "N/A"
        biography = "N/A" # Variable para la biografía

        # 1. Detectar privacidad
        private_text_elems = bot.find_elements(
            By.XPATH,
            "//span[contains(text(), 'privada') or contains(text(), 'private')]"
        )
        is_private = False
        for elem in private_text_elems:
            if "privada" in elem.text.lower() or "private" in elem.text.lower():
                is_private = True
                break
        
        # 2. Extraer Biografía (Intenta varios selectores comunes en vista móvil)
        try:
            # Opción A: Buscar el elemento h1 (nombre usuario) y buscar texto cercano
            # En vista móvil, la bio suele estar en un div con clase '_aacl' dentro del header
            # Usamos un XPATH genérico que busca divs con texto debajo del nombre
            bio_elem = bot.find_element(By.XPATH, "//div[contains(@class, '_aa_c')]//h1/../../following-sibling::div//div[contains(@class, '_aacl')]")
            biography = bio_elem.text
        except:
            try:
                # Opción B: Fallback más genérico
                bio_elem = bot.find_element(By.XPATH, "//div[@class='_aacl _aaco _aacu _aacx _aad6 _aade']")
                biography = bio_elem.text
            except:
                biography = "" # No tiene bio o no se encontró

        # 3. Extraer contadores
        if not is_private:
            try:
                followers_elem = WebDriverWait(bot, 4).until(
                    EC.presence_of_element_located((By.XPATH, "//a[contains(@href, '/followers/')]/span/span"))
                )
                following_elem = WebDriverWait(bot, 4).until(
                    EC.presence_of_element_located((By.XPATH, "//a[contains(@href, '/following/')]/span/span"))
                )
                num_followers = followers_elem.get_attribute("title") or followers_elem.text
                num_following = following_elem.get_attribute("title") or following_elem.text
            except Exception:
                pass
        else:
            # Perfil privado
            all_links = bot.find_elements(By.XPATH, "//a[@href='#']")
            for a in all_links:
                text = a.text.lower()
                try:
                    number_elem = a.find_element(By.XPATH, ".//span/span")
                    value = number_elem.get_attribute("title") or number_elem.text
                except Exception:
                    continue

                if "seguidores" in text or "followers" in text:
                    num_followers = value
                elif "seguidos" in text or "following" in text:
                    num_following = value

        # Normalizar números
        def limpiar_numero(valor):
            if not valor or valor == "N/A": return ""
            valor = valor.strip().replace("\xa0", "").replace(" ", "").replace(".", "").replace(",", "")
            if valor.lower().endswith("m"):
                return str(int(float(valor[:-1].replace(",", ".")) * 1_000_000))
            elif valor.lower().endswith("k"):
                return str(int(float(valor[:-1].replace(",", ".")) * 1_000))
            return valor if valor.isdigit() else ""

        num_followers = limpiar_numero(num_followers)
        num_following = limpiar_numero(num_following)
        
        fd_followers = num_followers[0] if num_followers else ""
        fd_following = num_following[0] if num_following else ""

        print(f"[Info] - {username} | Bio detectada: {'Sí' if len(biography)>1 else 'No'}")
        # Retornamos también la biografía
        return is_private, num_followers, fd_followers, num_following, fd_following, biography

    except TimeoutException:
        print(f"[Warning] - Timeout leyendo perfil de {username}")
        return "", "", "", "", "", ""
    except Exception as e:
        print(f"[Error] - Falló extracción de {username}: {e}")
        return "", "", "", "", "", ""

# ---------------------------------------------------------------------------
# Función: scrape_following (MODIFICADA: Ahora busca SEGUIDOS)
# ---------------------------------------------------------------------------
def scrape_following(bot, profile_username, user_input):
    """Abre la lista de SEGUIDOS (Following) e itera con scroll."""
    
    bot.get(f'https://www.instagram.com/{profile_username}/')
    human_delay(3, 6)

    # Cerrar popups
    popup_xpaths = ["//button[contains(text(), 'Ahora no')]", "//div[@aria-label='Cerrar']"]
    for xpath in popup_xpaths:
        try:
            bot.find_element(By.XPATH, xpath).click()
            human_delay(1, 2)
        except: pass

    try:
        WebDriverWait(bot, 15).until(
            EC.presence_of_element_located((By.XPATH, "//a[contains(@href, '/following')]"))
        ).click()
    except TimeoutException:
        print(f"[Error] - No se encontró el enlace de 'Seguidos' para {profile_username}. Puede ser privado o 0 seguidos.")
        return []

    human_delay(6, 10)
    print(f"[Info] - Scraping 'Following' list for {profile_username}...")

    users = set()
    scroll_count = 0
    max_scrolls = 150
    no_new_count = 0

    while len(users) < user_input and scroll_count < max_scrolls:
        # Busca elementos de usuarios en la lista
        followers_elements = bot.find_elements(
            By.XPATH,
            "//a[@role='link']/div/div/span[contains(@class,'_ap3a') and contains(@class,'_aaco')]"
        )

        new_users = 0
        for elem in followers_elements:
            try:
                u_name = elem.text.strip()
                banned = ["about", "explore", "api", "reels", "stories", "meta_verified"]
                
                if u_name and u_name not in users and len(u_name) > 1 and u_name.lower() not in banned:
                    users.add(u_name)
                    new_users += 1
                    print(f"{len(users)}. {u_name}")
            except: continue

        if new_users == 0:
            no_new_count += 1
            if no_new_count >= 4:
                print("No se encontraron más usuarios, parando.")
                break
        else:
            no_new_count = 0

        # Scroll
        bot.execute_script("window.scrollBy(0, 1500);")
        human_delay(2, 3)
        scroll_count += 1

    return list(users)[:user_input]

# -------------------------
# Lógica Principal de Scraping
# -------------------------
def scrapear_usuarios(bot, usernames, user_input):
    all_data = []
    num = 1
    profile_info = {}

    for user in usernames:
        user = user.strip()
        # Obtenemos datos del perfil PRINCIPAL (el que scrapeamos)
        is_priv, n_fol, fd_fol, n_fing, fd_fing, bio = get_profile_stats(bot, user)

        profile_info = {
            "user_name": user,
            "type_profile": "private" if is_priv else "public",
            "num_followers": n_fol,
            "num_following": n_fing,
            "biography": bio 
        }

        # Obtenemos la lista de SEGUIDOS (Following)
        following_list = scrape_following(bot, user, user_input)

        # Iteramos sobre cada usuario encontrado en la lista de seguidos
        for following_user in following_list:
            print(f"{num}. {following_user} --------------------")
            # Obtenemos stats y BIO de cada seguido
            is_priv_f, n_fol_f, fd_fol_f, n_fing_f, fd_fing_f, bio_f = get_profile_stats(bot, following_user)

            all_data.append({
                "num": num,
                "user_name": following_user, # Usuario de la lista
                "origin_profile": user,      # De quién lo sacamos
                "biography": bio_f,          # <--- NUEVO CAMPO: BIOGRAFÍA
                "type_profile": "private" if is_priv_f else "public",
                "num_followers": n_fol_f,
                "first_digit_followers": fd_fol_f,
                "num_following": n_fing_f,
                "first_digit_following": fd_fing_f
            })

            num += 1
            human_delay(3, 6) # Pausa de seguridad

    return all_data, profile_info

# -------------------------
# Funciones Excel / Benford
# -------------------------
def guardar_datos_excel(data, filename=None):
    if filename is None:
        filename = f"following_data_{int(time.time())}.xlsx"
    df = pd.DataFrame(data)
    # Reordenamos columnas para que bio salga visible
    cols = ["num", "user_name", "biography", "num_followers", "num_following", "type_profile", "first_digit_followers", "first_digit_following", "origin_profile"]
    # Aseguramos que solo usamos columnas que existen
    existing_cols = [c for c in cols if c in df.columns]
    df = df[existing_cols]
    
    df.to_excel(filename, index=False)
    print(f"[Success] - Datos guardados en {filename}")
    return filename

def agregar_frecuencias_primer_digito(excel_file):
    df = pd.read_excel(excel_file)
    cols = ["first_digit_followers", "first_digit_following"]
    
    # Limpieza previa
    for col in cols:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip().str[0]
            df[col] = df[col].where(df[col].str.isdigit(), pd.NA)

    with pd.ExcelWriter(excel_file, engine="openpyxl", mode="a") as writer:
        for col in cols:
            if col in df.columns:
                freq = df[col].value_counts().reindex([str(i) for i in range(10)], fill_value=0)
                freq_df = freq.reset_index()
                freq_df.columns = [col + "_digit", "frequency"]
                freq_df.to_excel(writer, sheet_name=col + "_freq", index=False)

# Nota: He comentado la función de PDF porque no estaba incluida en tu código original completo
# pero si la tienes definida, puedes descomentar la llamada abajo.
def generar_pdf_benford(excel_file, profile_info):
    print("[Info] - Generación de PDF omitida (Función no provista en el snippet original).")
    pass 

# -------------------------
# MAIN
# -------------------------
def scrape():
    credentials = load_credentials()
    if credentials is None: username, password = prompt_credentials()
    else: username, password = credentials

    user_input = int(input('[Required] - How many ACCOUNTS (following) to scrape: '))
    usernames = input("Enter the usernames to scrape (separated by commas): ").split(",")

    bot = iniciar_navegador()
    login(bot, username, password)

    # Scrapeo principal
    all_data, profile_info = scrapear_usuarios(bot, usernames, user_input)
    
    bot.quit()

    if all_data:
        excel_file = guardar_datos_excel(all_data)
        agregar_frecuencias_primer_digito(excel_file)
        generar_pdf_benford(excel_file, profile_info)
    else:
        print("[Info] - No se obtuvieron datos.")

if __name__ == '__main__':
    TIMEOUT = 15
    scrape()