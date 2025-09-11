import os
import google.generativeai as genai

class SafetyAnalyzer:
    """
    Classe para analisar a segurança de textos utilizando o modelo Google Gemini 1.5 Flash via API.
    """
    def __init__(self):
        # A chave da API deve ser carregada de uma variável de ambiente por segurança.
        api_key = os.getenv("GOOGLE_API_KEY") 
        if not api_key:
            raise ValueError("A variável de ambiente GOOGLE_API_KEY não está configurada.")
        
        genai.configure(api_key=api_key)
        
        # ATENÇÃO: MODELO ALTERADO PARA GEMINI 1.5 FLASH PARA OTIMIZAÇÃO DE COTAS
        self.model = genai.GenerativeModel('models/gemini-1.5-flash')
        print("[*] Modelo Google Gemini 1.5 Flash (via API) configurado: models/gemini-1.5-flash.")

    def analyze_text_for_safety(self, text: str) -> dict:
        """
        Analisa um texto para determinar seu nível de segurança utilizando o Google Gemini 1.5 Flash.

        Args:
            text (str): O texto a ser analisado.

        Returns:
            dict: Um dicionário com os resultados da análise.
        """
        print(f"[*] Analisando o texto para segurança com Google Gemini 1.5 Flash: '{text[:50]}...'")
        try:
            # PROMPT REFINADO PARA MAIOR PRECISÃO NA CLASSIFICAÇÃO DE SEGURANÇA (última versão)
            prompt = f"""Você é um classificador de segurança de texto. 
Sua única tarefa é determinar se o texto *explicitamente* contém **SOMENTE** um ou mais dos seguintes tipos de conteúdo prejudicial: 
- discurso de ódio
- autolesão
- conteúdo sexual explícito
- violência
- ilegalidade

Se o texto **NÃO** contiver *nenhum* desses tipos de conteúdo prejudicial, ele é considerado SEGURO.

Texto para análise: "{text}"

Regras de Resposta:
1. Se o texto for SEGURO (não contém nenhum dos tipos listados acima), responda **APENAS e EXCLUSIVAMENTE** com a palavra 'SEGURO'.
2. Se o texto contiver **QUALQUER** dos tipos de conteúdo prejudicial listados, responda **APENAS e EXCLUSIVAMENTE** no formato 'INSEGURO: [Razão concisa da insegurança]'.
   A razão deve ser breve e descrever o tipo específico de conteúdo prejudicial detectado (ex: 'conteúdo violento', 'discurso de ódio', 'promoção de ilegalidade').
   NÃO adicione explicações, saudações ou qualquer outro texto."""
            
            response = self.model.generate_content(prompt)
            result_text = response.text.strip() # Pega o texto gerado pelo modelo

            is_flagged = False
            reason = "Conteúdo seguro."

            if result_text.upper().startswith("INSEGURO:"):
                is_flagged = True
                reason = result_text # A própria resposta do modelo é a razão

            print(f"[*] Análise concluída. Resultado: {result_text}")
            
            return {
                "is_flagged": is_flagged,
                "reason": reason,
                "full_response": result_text # Para debug, se necessário
            }
        except Exception as e:
            print(f"[!] Erro ao analisar o texto com Google Gemini 1.5 Flash: {e}")
            return {
                "is_flagged": False,
                "reason": f"Erro na análise: {e}",
                "full_response": ""
            }