import sys
import os

# Adiciona a pasta 'src' ao Python path para que ele possa encontrar 'safety_ai_app'
# Esta linha é vital para testar importações de pacotes em estruturas de projeto
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

try:
    from safety_ai_app.nr_rag_qa import NRQuestionAnswering
    print("✅ Importação de 'safety_ai_app.nr_rag_qa' bem-sucedida!")
    # Se quiser, pode tentar instanciar:
    # qa = NRQuestionAnswering()
    # print("NRQuestionAnswering instanciada com sucesso!")
except ModuleNotFoundError as e:
    print(f"❌ Erro de importação: {e}")
    print("Caminho de busca do Python (sys.path):")
    for p in sys.path:
        print(f"- {p}")
except Exception as e:
    print(f"❌ Ocorreu um erro inesperado: {e}")
