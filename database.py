from supabase import create_client, Client
from datetime import datetime

# --- CONFIGURAÇÃO DO BANCO DE DADOS ---
SUPABASE_URL = "https://soihehwfewiemzkswevm.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InNvaWhlaHdmZXdpZW16a3N3ZXZtIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1NzgxODI3OSwiZXhwIjoyMDczMzk0Mjc5fQ.ArQbaeVAQNwlkJQK5uSqVzdyECWYQ8OrCjBZ4KZ_pOg"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- FUNÇÃO PARA SALVAR A CONSULTA (ATUALIZADA) ---
def salvar_log_consulta(dados_da_consulta):
    """
    Recebe um dicionário com os dados da consulta, converte os tipos
    e os insere na tabela 'consultas' do Supabase.
    """
    try:
        # ========================================================================
        # >> NOVA LÓGICA DE CONVERSÃO DE TIPOS <<
        # ========================================================================
        
        # --- Converte 'sequencial' para número inteiro ---
        sequencial_texto = dados_da_consulta.get('Sequencial')
        sequencial_numero = None
        if sequencial_texto and sequencial_texto.isdigit():
            sequencial_numero = int(sequencial_texto)
            
        # --- Converte 'vencimento_inscricao' para data (formato AAAA-MM-DD) ---
        vencimento_texto = dados_da_consulta.get('Vencimento_Inscricao')
        vencimento_data = None
        if vencimento_texto:
            # Tenta converter o formato DD/MM/AAAA para AAAA-MM-DD
            try:
                # O objeto datetime é criado a partir do formato brasileiro
                data_obj = datetime.strptime(vencimento_texto, '%d/%m/%Y')
                # O formato para o banco é extraído do objeto
                vencimento_data = data_obj.strftime('%Y-%m-%d')
            except ValueError:
                print(f"Alerta: não foi possível converter a data '{vencimento_texto}'. Será salvo como nulo.")
                vencimento_data = None # Se o formato for inesperado, salva como nulo

        # ========================================================================

        # Prepara o objeto para ser salvo, agora com os tipos corretos
        dados_para_salvar = {
            'id_solicitante': dados_da_consulta['ID_Solicitante'],
            'id_licitacao': dados_da_consulta['ID_Licitacao'],
            'tipo_consulta': dados_da_consulta['Tipo_Consulta'],
            'documento_consultado': dados_da_consulta['CNPJ_CPF'],
            'sequencial': sequencial_numero, # <-- Usa a variável convertida
            'razao_social': dados_da_consulta['Razao_Social'],
            'nm_inscricao': dados_da_consulta['Nm_inscricao'],
            'tipo_inscricao': dados_da_consulta['Tipo_Inscricao'],
            'vencimento_inscricao': vencimento_data, # <-- Usa a variável convertida
            'situacao': dados_da_consulta['Situacao'],
            'tempo_processamento': dados_da_consulta['Tempo_Processamento'],
            'mensagem_api': dados_da_consulta['Mensagem_API'],
            'ip_requisitante': dados_da_consulta.get('ip_requisitante'),
            # O timestamp_consulta é preenchido automaticamente pelo Supabase
        }
        
        supabase.table('consultas').insert(dados_para_salvar).execute()
        print(f">>> Log da consulta do IP {dados_para_salvar['ip_requisitante']} salvo no banco de dados.")

    except Exception as e:
        print(f"!!! ERRO ao salvar no banco de dados: {e}")