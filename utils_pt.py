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
            
            # Define a largura máxima como 50 caracteres para legibilidade
            adjusted_width = min(max_length + 2, 50)
            worksheet.column_dimensions[column_letter].width = adjusted_width
        
        # Adiciona uma planilha de resumo
        summary_data = {
            "Métrica": [
                "Total de Artigos",
                "Artigos com Título",
                "Artigos com Autores", 
                "Artigos com Ano",
                "Artigos com DOI",
                "Artigos com Resumo"
            ],
            "Contagem": [
                len(df),
                len(df[df["Title"] != "Sem informação"]),
                len(df[df["Authors"] != "Sem informação"]),
                len(df[df["Year"] != "Sem informação"]),
                len(df[df["DOI"] != "Sem informação"]),
                len(df[df["Abstract"] != "Sem informação"])
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
    
    buffer.seek(0)
    return buffer.getvalue()

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
    
    # Remove pontuação final
    doi_str = doi_str.rstrip(".,;")
    
    return doi_str if doi_str else "Sem informação"

