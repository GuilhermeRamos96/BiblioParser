import pandas as pd
import io
from typing import List, Tuple, Any

def validate_files(uploaded_files: List[Any]) -> Tuple[List[Any], List[str]]:
    """Valida os arquivos enviados e retorna os arquivos válidos e os nomes dos arquivos inválidos"""
    valid_files = []
    invalid_files = []
    
    for file in uploaded_files:
        try:
            # Verifica a extensão do arquivo
            if not file.name.lower().endswith((".ris", ".txt")):
                invalid_files.append(file.name)
                continue
            
            # Verifica se o arquivo é legível
            file.seek(0)  # Reseta o ponteiro do arquivo
            content = file.read(100)  # Lê os primeiros 100 bytes para testar
            file.seek(0)  # Reseta o ponteiro do arquivo
            
            if len(content) == 0:
                invalid_files.append(file.name)
                continue
            
            valid_files.append(file)
            
        except Exception as e:
            invalid_files.append(file.name)
    
    return valid_files, invalid_files

def create_excel_file(df: pd.DataFrame) -> bytes:
    """Cria um arquivo Excel a partir do DataFrame e retorna como bytes"""
    buffer = io.BytesIO()
    
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        # Escreve os dados principais
        df.to_excel(writer, sheet_name="Dados Bibliográficos", index=False)
        
        # Obtém o workbook e a worksheet
        workbook = writer.book
        worksheet = writer.sheets["Dados Bibliográficos"]
        
        # Auto-ajusta a largura das colunas
        for column in worksheet.columns:
            max_length = 0
            column_letter = column[0].column_letter
            
            for cell in column:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            
            # Define a largura máxima como 80 caracteres para melhor legibilidade
            adjusted_width = min(max_length + 2, 80)
            worksheet.column_dimensions[column_letter].width = adjusted_width
        
        # Adiciona uma planilha de resumo com estatísticas expandidas
        summary_data = {
            "Métrica": [
                "Total de Artigos",
                "Artigos com Título",
                "Artigos com Autores", 
                "Artigos com Ano",
                "Artigos com DOI",
                "Artigos com Resumo",
                "Completude Média (%)",
                "Artigos Completos (todos os campos)"
            ],
            "Contagem": [
                len(df),
                len(df[df["Title"] != "Sem informação"]),
                len(df[df["Authors"] != "Sem informação"]),
                len(df[df["Year"] != "Sem informação"]),
                len(df[df["DOI"] != "Sem informação"]),
                len(df[df["Abstract"] != "Sem informação"]),
                round(calculate_completeness_percentage(df), 1),
                count_complete_articles(df)
            ]
        }
        
        summary_df = pd.DataFrame(summary_data)
        summary_df.to_excel(writer, sheet_name="Resumo", index=False)
        
        # Auto-ajusta as colunas da planilha de resumo
        summary_sheet = writer.sheets["Resumo"]
        for column in summary_sheet.columns:
            max_length = 0
            column_letter = column[0].column_letter
            
            for cell in column:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            
            adjusted_width = max_length + 2
            summary_sheet.column_dimensions[column_letter].width = adjusted_width
        
        # Adiciona planilha de análise por arquivo de origem (se disponível)
        if "source_file" in df.columns:
            file_analysis = analyze_by_source_file(df)
            file_analysis.to_excel(writer, sheet_name="Análise por Arquivo", index=False)
            
            # Auto-ajusta as colunas da planilha de análise por arquivo
            file_sheet = writer.sheets["Análise por Arquivo"]
            for column in file_sheet.columns:
                max_length = 0
                column_letter = column[0].column_letter
                
                for cell in column:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass
                
                adjusted_width = min(max_length + 2, 50)
                file_sheet.column_dimensions[column_letter].width = adjusted_width
    
    buffer.seek(0)
    return buffer.getvalue()

def calculate_completeness_percentage(df: pd.DataFrame) -> float:
    """Calcula a porcentagem média de completude dos dados"""
    if df.empty:
        return 0.0
    
    required_fields = ["Title", "Authors", "Year", "DOI", "Abstract"]
    total_fields = len(required_fields)
    total_articles = len(df)
    
    if total_articles == 0:
        return 0.0
    
    completed_fields = 0
    for field in required_fields:
        if field in df.columns:
            completed_fields += len(df[df[field] != "Sem informação"])
    
    return (completed_fields / (total_fields * total_articles)) * 100

def count_complete_articles(df: pd.DataFrame) -> int:
    """Conta artigos que têm todos os campos preenchidos"""
    if df.empty:
        return 0
    
    required_fields = ["Title", "Authors", "Year", "DOI", "Abstract"]
    complete_mask = True
    
    for field in required_fields:
        if field in df.columns:
            complete_mask &= (df[field] != "Sem informação")
        else:
            return 0  # Se algum campo obrigatório não existe, nenhum artigo está completo
    
    return len(df[complete_mask])

def analyze_by_source_file(df: pd.DataFrame) -> pd.DataFrame:
    """Analisa estatísticas por arquivo de origem"""
    if "source_file" not in df.columns:
        return pd.DataFrame()
    
    analysis_data = []
    
    for filename in df["source_file"].unique():
        file_df = df[df["source_file"] == filename]
        
        analysis_data.append({
            "Arquivo": filename,
            "Total de Artigos": len(file_df),
            "Com Título": len(file_df[file_df["Title"] != "Sem informação"]),
            "Com Autores": len(file_df[file_df["Authors"] != "Sem informação"]),
            "Com Ano": len(file_df[file_df["Year"] != "Sem informação"]),
            "Com DOI": len(file_df[file_df["DOI"] != "Sem informação"]),
            "Com Resumo": len(file_df[file_df["Abstract"] != "Sem informação"]),
            "Completude (%)": round(calculate_completeness_percentage(file_df), 1),
            "Artigos Completos": count_complete_articles(file_df)
        })
    
    return pd.DataFrame(analysis_data)

def clean_text(text: str) -> str:
    """Limpa e normaliza o conteúdo do texto"""
    if not text or text == "Sem informação":
        return "Sem informação"
    
    # Remove espaços em branco extras e novas linhas
    text = " ".join(text.split())
    
    # Remove quaisquer caracteres não imprimíveis
    text = "".join(char for char in text if char.isprintable() or char.isspace())
    
    return text.strip()

def extract_year_from_date(date_str: str) -> str:
    """Extrai o ano de vários formatos de data"""
    import re
    
    if not date_str:
        return "Sem informação"
    
    # Procura por ano de 4 dígitos
    year_match = re.search(r"\b(19|20)\d{2}\b", str(date_str))
    if year_match:
        return year_match.group()
    
    return "Sem informação"

def normalize_doi(doi_str: str) -> str:
    """Normaliza o formato do DOI"""
    if not doi_str or doi_str == "Sem informação":
        return "Sem informação"
    
    # Remove prefixos comuns
    doi_str = doi_str.replace("doi:", "").replace("DOI:", "").strip()
    doi_str = doi_str.replace("https://doi.org/", "").replace("http://dx.doi.org/", "")
    
    # Remove pontuação final
    doi_str = doi_str.rstrip(".,;")
    
    return doi_str if doi_str else "Sem informação"

def validate_doi_format(doi: str) -> bool:
    """Valida se o DOI tem formato válido"""
    import re
    
    if not doi or doi == "Sem informação":
        return False
    
    # Formato básico do DOI: 10.XXXX/YYYY
    return bool(re.match(r"^10\.\d+/.+", doi.strip()))

def calculate_similarity_score(text1: str, text2: str) -> float:
    """Calcula pontuação de similaridade entre dois textos"""
    if not text1 or not text2 or text1 == "Sem informação" or text2 == "Sem informação":
        return 0.0
    
    # Normaliza os textos
    import re
    
    text1_norm = re.sub(r"[^\w\s]", "", text1.lower())
    text2_norm = re.sub(r"[^\w\s]", "", text2.lower())
    
    words1 = set(text1_norm.split())
    words2 = set(text2_norm.split())
    
    if len(words1) == 0 or len(words2) == 0:
        return 0.0
    
    # Similaridade de Jaccard
    intersection = len(words1.intersection(words2))
    union = len(words1.union(words2))
    
    return intersection / union if union > 0 else 0.0
