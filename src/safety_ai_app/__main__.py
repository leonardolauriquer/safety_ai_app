import argparse
import os
import sys
import csv
from datetime import datetime
from io import StringIO # Importado para ajudar a parsear linhas CSV
from safety_ai_app.safety_analyzer import SafetyAnalyzer

def _initialize_analyzer():
    """Tenta inicializar o SafetyAnalyzer e lida com erros de configuração."""
    try:
        analyzer = SafetyAnalyzer()
        return analyzer
    except ValueError as e:
        print(f"Erro de configuração: {e}")
        print("Por favor, certifique-se de que a variável de ambiente GOOGLE_API_KEY está configurada corretamente.")
        sys.exit(1) # Sai do programa se a API key não estiver configurada

def run_interactive_mode():
    """Executa o aplicativo em modo interativo."""
    analyzer = _initialize_analyzer() # Inicializa o analisador

    print("\n--- Iniciando safety-ai-app ---")
    print("\nsafety-ai-app CLI: Olá, Leo! Tudo pronto para revolucionar com IA.")
    # Mensagem atualizada para refletir o modelo em uso
    print("Vamos analisar a segurança de um texto utilizando o Google Gemini 1.5 Flash (API gratuita)!")

    while True:
        text_input = input("\nDigite o texto para análise de segurança (ou 'sair' para encerrar): ")
        if text_input.lower() == 'sair':
            print("Encerrando a sessão. Até mais!")
            break
        
        if not text_input.strip():
            print("Por favor, digite algum texto para análise.")
            continue

        result = analyzer.analyze_text_for_safety(text_input)
        
        if result["is_flagged"]:
            print(f"\n[!!!] ATENÇÃO: O texto foi SINALIZADO como INSEGURO!")
            print(f"Razão: {result['reason']}")
        else:
            print(f"\n[OK] O texto parece SEGURO.")
            print(f"Razão: {result['reason']}")
        
    print("Encerrando a análise de segurança. Até a próxima!")

def run_batch_mode(input_filepath, output_filepath):
    """Executa o aplicativo em modo de processamento em lote."""
    analyzer = _initialize_analyzer() # Inicializa o analisador
    
    print(f"\n--- Iniciando safety-ai-app em modo lote ---")
    print(f"Lendo textos de: {input_filepath}")
    print(f"Escrevendo resultados em: {output_filepath}")

    processed_count = 0
    start_time = datetime.now()

    try:
        is_csv = input_filepath.lower().endswith('.csv')

        with open(input_filepath, 'r', encoding='utf-8') as infile:
            reader_obj = None
            header_offset = 0 # Para ajustar a contagem de linhas se houver cabeçalho

            if is_csv:
                reader_obj = csv.reader(infile)
                header = next(reader_obj, None) # Lê o cabeçalho, se houver
                if header:
                    header_offset = 1 # Aumenta o offset se um cabeçalho foi lido
            else: # Arquivo de texto simples, um texto por linha
                reader_obj = (line.strip() for line in infile) # Gerador de linhas já sem espaços
            
            output_header = ['texto_original', 'e_inseguro', 'razao_inseguranca', 'resposta_completa_modelo']
            
            with open(output_filepath, 'w', newline='', encoding='utf-8') as outfile:
                writer = csv.writer(outfile)
                writer.writerow(output_header) # Escreve o cabeçalho no arquivo de saída

                # Itera sobre os dados
                for i, row_data in enumerate(reader_obj):
                    text_to_analyze_batch = ""

                    if is_csv:
                        if row_data:
                            text_to_analyze_batch = row_data[0].strip() # Assume o texto na primeira coluna
                        else:
                            continue # Pula linhas vazias no CSV
                    else: # Arquivo de texto simples, row_data já é o texto da linha
                        text_to_analyze_batch = row_data

                    if not text_to_analyze_batch: # Pula textos vazios após stripping
                        continue

                    # Adiciona 1 ao índice e o offset do cabeçalho para exibir o número correto da linha original
                    print(f"[*] Processando linha {i + 1 + header_offset}: '{text_to_analyze_batch[:70]}...'")
                    result = analyzer.analyze_text_for_safety(text_to_analyze_batch)
                    
                    writer.writerow([
                        text_to_analyze_batch,
                        'SIM' if result['is_flagged'] else 'NÃO',
                        result['reason'],
                        result['full_response']
                    ])
                    processed_count += 1
        
        end_time = datetime.now()
        duration = end_time - start_time
        print(f"\n--- Processamento em lote concluído ---")
        print(f"Total de textos analisados: {processed_count}")
        print(f"Tempo total: {duration}")
        print(f"Resultados salvos em: {output_filepath}")

    except FileNotFoundError:
        print(f"[ERRO] Arquivo de entrada não encontrado: {input_filepath}")
        sys.exit(1)
    except Exception as e:
        print(f"[ERRO] Ocorreu um erro durante o processamento em lote: {e}")
        # Para depuração, podemos imprimir o rastreamento completo da exceção
        # import traceback
        # traceback.print_exc()
        sys.exit(1)

def main():
    """Entry point para o CLI safety-ai-app."""
    parser = argparse.ArgumentParser(description="Aplicativo de análise de segurança de texto.")
    parser.add_argument(
        '-i', '--input-file', 
        type=str, 
        help='Caminho para o arquivo de entrada com textos para análise em lote (um texto por linha ou primeira coluna de CSV). Ex: textos.txt ou textos.csv'
    )
    parser.add_argument(
        '-o', '--output-file', 
        type=str, 
        help='Caminho para o arquivo de saída onde os resultados do lote serão salvos (CSV). Ex: resultados.csv'
    )

    args = parser.parse_args()

    if args.input_file and args.output_file:
        run_batch_mode(args.input_file, args.output_file)
    elif args.input_file or args.output_file:
        # Se apenas um dos arquivos for fornecido, avisar o usuário
        print("[ERRO] Para o modo de processamento em lote, ambos --input-file e --output-file devem ser fornecidos.")
        parser.print_help()
        sys.exit(1)
    else:
        # Se nenhum argumento de arquivo for fornecido, executa o modo interativo
        run_interactive_mode()

if __name__ == "__main__":
    main()
