# -*- coding: utf-8 -*-
import time
from datetime import datetime
from flask import Flask, request, jsonify
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup

# >> MUDANÇA IMPORTANTE: Importa a função do nosso novo arquivo
from database import salvar_log_consulta

# As credenciais do Supabase NÃO ficam mais aqui!

app = Flask(__name__)

# --- FUNÇÃO DE WEB SCRAPING (VERSÃO CORRETA PARA O RENDER) ---
def buscar_dados_no_site(tipo_consulta, documento):
    print(f"--- Iniciando Web Scraping com Selenium para {tipo_consulta}: {documento} ---")
    
    dados_retornados = {}
    lista_de_resultados = []
    driver = None 

    try:
        # Estas opções são CRÍTICAS para o ambiente do Render
        options = webdriver.ChromeOptions()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--log-level=3')
        
        # No Render, o Service() é chamado sem caminho, pois os buildpacks instalam o driver
        service = Service()
        
        driver = webdriver.Chrome(service=service, options=options)
        
        # O resto do código continua o mesmo...
        url_alvo = "https://www.incorpnet.com.br/appincorpnet2_crnsp/incorpnet.dll/controller?pagina=pub_mvcLocalizarCadastro.htm"
        driver.get(url_alvo)
        wait = WebDriverWait(driver, 10)

        if tipo_consulta.upper() == 'CNPJ':
            campo_documento = wait.until(EC.element_to_be_clickable((By.ID, 'EDT_CNPJ')))
        else:
            campo_documento = wait.until(EC.element_to_be_clickable((By.ID, 'EDT_CPF')))
        
        campo_documento.send_keys(documento)
        botao_pesquisar = wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@id="botoes"]/div/input[1]')))
        botao_pesquisar.click()
        wait.until(EC.presence_of_element_located((By.ID, 'tabelaResultado')))

        html_resultados = driver.page_source
        soup = BeautifulSoup(html_resultados, 'html.parser')

        # ... (a lógica de extração da tabela continua a mesma)
        tabela = soup.find('table', id='tabelaResultado')
        if tabela:
            # ...
            if not lista_de_resultados:
                dados_retornados['codigo_retorno'] = 3
            else:
                dados_retornados['codigo_retorno'] = 0
    
    except TimeoutException:
        print("ERRO: Timeout!")
        dados_retornados['codigo_retorno'] = 2
    except Exception as e:
        print(f"ERRO inesperado no scraping: {e}")
        dados_retornados['codigo_retorno'] = 99
        dados_retornados['detalhe_erro'] = str(e)
    finally:
        if driver:
            driver.quit()

    dados_retornados['resultados'] = lista_de_resultados
    return dados_retornados

# --- ROTA DA API (MAIS LIMPA) ---
@app.route('/consulta', methods=['POST'])
def realizar_consulta():
    start_time = time.time()
    dados_entrada = request.get_json()
    
    if request.headers.getlist("X-Forwarded-For"):
       ip_requisitante = request.headers.getlist("X-Forwarded-For")[0]
    else:
       ip_requisitante = request.remote_addr
    
    # Validação (continua a mesma)
    campos_obrigatorios = ['ID_Solicitante', 'ID_Licitacao', 'Tipo_Consulta', 'CNPJ_CPF']
    if not dados_entrada or not all(dados_entrada.get(campo) for campo in campos_obrigatorios):
        # ... (código de erro de falta de parâmetros)
        return jsonify({"Mensagem_API": "1 - Falta de parâmetros"}), 400

    # Lógica principal (continua a mesma)
    tipo_consulta = dados_entrada.get('Tipo_Consulta')
    cnpj_cpf = dados_entrada.get('CNPJ_CPF')
    resultado_scraping = buscar_dados_no_site(tipo_consulta, cnpj_cpf)
    
    end_time = time.time()
    json_final = {
        "ID_Solicitante": dados_entrada.get('ID_Solicitante'),
        "ID_Licitacao": dados_entrada.get('ID_Licitacao'),
        # ... (resto da montagem do json_final)
        "Tipo_Consulta": tipo_consulta, "CNPJ_CPF": cnpj_cpf, "Sequencial": "", 
        "Razao_Social": "", "Nm_inscricao": "", "Tipo_Inscricao": "", 
        "Vencimento_Inscricao": "", "Situacao": "",
        "Tempo_Processamento": f"{(end_time - start_time):.2f} segundos", "Mensagem_API": ""
    }
    
    codigo = resultado_scraping.get('codigo_retorno')
    if codigo == 0:
        json_final['Mensagem_API'] = "Ok"
        primeiro_resultado = resultado_scraping['resultados'][0]
        json_final.update(primeiro_resultado)
    elif codigo == 2:
        json_final['Mensagem_API'] = "Timeout Fonte"
    elif codigo == 3:
        json_final['Mensagem_API'] = "CNPJ/CPF Não encontrado"
    else:
        json_final['Mensagem_API'] = "Erro desconhecido na fonte"

    # >> MUDANÇA IMPORTANTE: Salva no banco de dados <<
    # Adicionamos o IP ao dicionário para ser salvo
    json_final['ip_requisitante'] = ip_requisitante 
    # Chamamos nossa nova função centralizada
    salvar_log_consulta(json_final)

    # Removemos o IP do JSON de resposta para o cliente, por segurança.
    del json_final['ip_requisitante']

    return jsonify(json_final)

# --- Inicia o servidor ---
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)