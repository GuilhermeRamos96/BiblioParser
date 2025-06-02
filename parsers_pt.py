import re
import rispy
from typing import List, Dict, Any, Optional
from io import StringIO

class RISParser:
    """Parser para arquivos no formato RIS"""
    
    def parse(self, file_content: bytes) -> List[Dict[str, Any]]:
        """Analisa o conteúdo do arquivo RIS e extrai dados bibliográficos"""
        articles = []
        
        try:
            # Decodifica o conteúdo do arquivo
            text_content = file_content.decode("utf-8", errors="ignore")
            
            # Usa rispy para analisar o conteúdo RIS
            ris_entries = rispy.loads(text_content)
            
            for entry in ris_entries:
                article = self._extract_ris_fields(entry)
                articles.append(article)
                
        except Exception as e:
            # Recorre à análise personalizada se o rispy falhar
            articles = self._custom_ris_parse(file_content)
        
        return articles
    
    def _extract_ris_fields(self, entry: Dict[str, Any]) -> Dict[str, Any]:
        """Extrai os campos necessários da entrada RIS"""
        article = {
            "Title": "Sem informação",
            "Authors": "Sem informação", 
            "Year": "Sem informação",
            "DOI": "Sem informação",
            "Abstract": "Sem informação"
        }
        
        # Título
        if "title" in entry or "primary_title" in entry:
            title = entry.get("title") or entry.get("primary_title")
            if title:
                article["Title"] = str(title).strip()
        
        # Autores
        authors = []
        if "authors" in entry and entry["authors"]:
            authors = [str(author).strip() for author in entry["authors"] if author]
        elif "first_authors" in entry and entry["first_authors"]:
            authors = [str(author).strip() for author in entry["first_authors"] if author]
        
        if authors:
            article["Authors"] = ", ".join(authors)
        
        # Ano
        year = entry.get("year") or entry.get("publication_year")
        if year:
            # Extrai o ano de vários formatos de data
            year_match = re.search(r"\b(19|20)\d{2}\b", str(year))
            if year_match:
                article["Year"] = year_match.group()
        
        # DOI
        doi = entry.get("doi")
        if doi:
            article["DOI"] = str(doi).strip()
        
        # Resumo
        abstract = entry.get("abstract")
        if abstract:
            article["Abstract"] = str(abstract).strip()
        
        return article
    
    def _custom_ris_parse(self, file_content: bytes) -> List[Dict[str, Any]]:
        """Parser RIS personalizado como fallback"""
        articles = []
        
        try:
            text_content = file_content.decode("utf-8", errors="ignore")
            
            # Divide em registros individuais
            records = re.split(r"\nER\s*-", text_content)
            
            for record in records:
                if not record.strip():
                    continue
                
                article = {
                    "Title": "Sem informação",
                    "Authors": "Sem informação",
                    "Year": "Sem informação", 
                    "DOI": "Sem informação",
                    "Abstract": "Sem informação"
                }
                
                # Extrai título
                title_match = re.search(r"^TI\s*-\s*(.+?)(?=\n[A-Z]{2}\s*-|\Z)", record, re.MULTILINE | re.DOTALL)
                if title_match:
                    article["Title"] = title_match.group(1).strip().replace("\n", " ")
                
                # Extrai autores
                author_matches = re.findall(r"^AU\s*-\s*(.+?)$", record, re.MULTILINE)
                if author_matches:
                    authors = [author.strip() for author in author_matches if author.strip()]
                    if authors:
                        article["Authors"] = ", ".join(authors)
                
                # Extrai ano
                year_match = re.search(r"^PY\s*-\s*(\d{4})", record, re.MULTILINE)
                if not year_match:
                    year_match = re.search(r"^DA\s*-\s*(\d{4})", record, re.MULTILINE)
                if year_match:
                    article["Year"] = year_match.group(1)
                
                # Extrai DOI
                doi_match = re.search(r"^DO\s*-\s*(.+?)$", record, re.MULTILINE)
                if doi_match:
                    article["DOI"] = doi_match.group(1).strip()
                
                # Extrai resumo
                abstract_match = re.search(r"^AB\s*-\s*(.+?)(?=\n[A-Z]{2}\s*-|\Z)", record, re.MULTILINE | re.DOTALL)
                if abstract_match:
                    article["Abstract"] = abstract_match.group(1).strip().replace("\n", " ")
                
                articles.append(article)
                
        except Exception as e:
            print(f"Erro na análise RIS personalizada: {e}")
        
        return articles


class TXTParser:
    """Parser para arquivos no formato TXT (estilo PubMed)"""
    
    def parse(self, file_content: bytes) -> List[Dict[str, Any]]:
        """Analisa o conteúdo do arquivo TXT e extrai dados bibliográficos"""
        articles = []
        
        try:
            # Decodifica o conteúdo do arquivo
            text_content = file_content.decode("utf-8", errors="ignore")
            
            # Divide em registros individuais (assumindo que os registros são separados por linhas em branco)
            records = re.split(r"\n\s*\n", text_content)
            
            for record in records:
                if not record.strip():
                    continue
                
                article = self._extract_txt_fields(record)
                if any(value != "Sem informação" for value in article.values()):
                    articles.append(article)
                    
        except Exception as e:
            print(f"Erro ao analisar o arquivo TXT: {e}")
        
        return articles
    
    def _extract_txt_fields(self, record: str) -> Dict[str, Any]:
        """Extrai os campos necessários do registro TXT"""
        article = {
            "Title": "Sem informação",
            "Authors": "Sem informação",
            "Year": "Sem informação", 
            "DOI": "Sem informação",
            "Abstract": "Sem informação"
        }
        
        lines = record.split("\n")
        current_field = None
        current_content = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Verifica se a linha começa com um identificador de campo
            field_match = re.match(r"^([A-Z]+)\s*-\s*(.*)$", line)
            
            if field_match:
                # Processa o campo anterior
                if current_field and current_content:
                    self._process_field(article, current_field, " ".join(current_content))
                
                # Inicia novo campo
                current_field = field_match.group(1)
                current_content = [field_match.group(2)] if field_match.group(2) else []
            else:
                # Continuação do campo atual
                if current_field:
                    current_content.append(line)
        
        # Processa o último campo
        if current_field and current_content:
            self._process_field(article, current_field, " ".join(current_content))
        
        return article
    
    def _process_field(self, article: Dict[str, Any], field_code: str, content: str):
        """Processa campo individual com base no código do campo"""
        content = content.strip()
        if not content:
            return
        
        # Título
        if field_code == "TI":
            article["Title"] = content
        
        # Autores
        elif field_code in ["AU", "FAU"]:
            if article["Authors"] == "Sem informação":
                article["Authors"] = content
            else:
                article["Authors"] += ", " + content
        
        # Data de Publicação (extrai ano)
        elif field_code == "DP":
            year_match = re.search(r"\b(19|20)\d{2}\b", content)
            if year_match:
                article["Year"] = year_match.group()
        
        # Resumo
        elif field_code == "AB":
            article["Abstract"] = content
        
        # DOI (procura por tag [doi])
        elif field_code in ["AID", "LID"]:
            doi_match = re.search(r"(.+?)\s*\[doi\]", content, re.IGNORECASE)
            if doi_match:
                article["DOI"] = doi_match.group(1).strip()

