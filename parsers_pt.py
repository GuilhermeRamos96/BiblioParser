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
            # Limpa e normaliza o DOI
            doi_cleaned = self._clean_doi(str(doi))
            if doi_cleaned:
                article["DOI"] = doi_cleaned
        
        # Resumo
        abstract = entry.get("abstract")
        if abstract:
            abstract_cleaned = self._clean_abstract(str(abstract))
            if abstract_cleaned:
                article["Abstract"] = abstract_cleaned
        
        return article
    
    def _clean_doi(self, doi: str) -> Optional[str]:
        """Limpa e valida o formato do DOI"""
        if not doi:
            return None
            
        # Remove prefixos comuns e espaços
        doi = doi.replace("doi:", "").replace("DOI:", "").strip()
        doi = doi.replace("https://doi.org/", "").replace("http://dx.doi.org/", "")
        doi = doi.rstrip(".,;")
        
        # Valida formato básico do DOI
        if re.match(r"^10\.\d+/.+", doi):
            return doi
            
        return None
    
    def _clean_abstract(self, abstract: str) -> Optional[str]:
        """Limpa e formata o resumo"""
        if not abstract:
            return None
            
        # Remove tags HTML se presentes
        abstract = re.sub(r"<[^>]+>", "", abstract)
        
        # Remove espaços em branco extras e quebras de linha desnecessárias
        abstract = " ".join(abstract.split())
        
        # Remove caracteres não imprimíveis
        abstract = "".join(char for char in abstract if char.isprintable() or char.isspace())
        
        abstract = abstract.strip()
        
        # Verifica se o resumo tem conteúdo útil (mais de 10 caracteres)
        if len(abstract) > 10:
            return abstract
            
        return None
    
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
                    title = title_match.group(1).strip().replace("\n", " ")
                    title = " ".join(title.split())  # Remove espaços extras
                    if title:
                        article["Title"] = title
                
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
                    doi_raw = doi_match.group(1).strip()
                    doi_cleaned = self._clean_doi(doi_raw)
                    if doi_cleaned:
                        article["DOI"] = doi_cleaned
                
                # Extrai resumo
                abstract_match = re.search(r"^AB\s*-\s*(.+?)(?=\n[A-Z]{2}\s*-|\Z)", record, re.MULTILINE | re.DOTALL)
                if abstract_match:
                    abstract_raw = abstract_match.group(1).strip().replace("\n", " ")
                    abstract_cleaned = self._clean_abstract(abstract_raw)
                    if abstract_cleaned:
                        article["Abstract"] = abstract_cleaned
                
                articles.append(article)
                
        except Exception as e:
            print(f"Erro na análise RIS personalizada: {e}")
        
        return articles


class TXTParser:
    """Parser para arquivos no formato TXT (múltiplos formatos: PubMed, campos completos, e tags de duas letras)"""
    
    def parse(self, file_content: bytes) -> List[Dict[str, Any]]:
        """Analisa o conteúdo do arquivo TXT e extrai dados bibliográficos"""
        articles = []
        
        try:
            # Decodifica o conteúdo do arquivo
            text_content = file_content.decode("utf-8", errors="ignore")
            
            # Detecta o formato do arquivo
            format_type = self._detect_format(text_content)
            
            # Divide em registros usando uma abordagem mais simples
            records = self._split_records(text_content, format_type)
            
            for record in records:
                if not record.strip():
                    continue
                
                article = self._extract_txt_fields(record, format_type)
                if any(value != "Sem informação" for value in article.values()):
                    articles.append(article)
                    
        except Exception as e:
            print(f"Erro ao analisar o arquivo TXT: {e}")
        
        return articles
    
    def _split_records(self, text_content: str, format_type: str) -> List[str]:
        """Divide o texto em registros individuais baseado no formato"""
        records = []
        
        if format_type == "citation_export":
            # Procura por todas as posições de "Record #"
            record_positions = []
            for match in re.finditer(r"Record #\d+ of \d+", text_content):
                record_positions.append(match.start())
            
            # Divide o texto nas posições encontradas
            for i in range(len(record_positions)):
                start = record_positions[i]
                end = record_positions[i + 1] if i + 1 < len(record_positions) else len(text_content)
                record = text_content[start:end].strip()
                if record:
                    records.append(record)
                    
        elif format_type == "records_format":
            # Procura por todas as posições de "RECORD"
            record_positions = []
            for match in re.finditer(r"^RECORD \d+", text_content, re.MULTILINE):
                record_positions.append(match.start())
            
            # Divide o texto nas posições encontradas
            for i in range(len(record_positions)):
                start = record_positions[i]
                end = record_positions[i + 1] if i + 1 < len(record_positions) else len(text_content)
                record = text_content[start:end].strip()
                if record:
                    records.append(record)
                    
        elif format_type == "er_terminated":
            # Divide por terminadores ER
            records = re.split(r"\nER\s*-?\s*\n", text_content)
            records = [r.strip() for r in records if r.strip()]
            
        else:
            # Formato PubMed: procura por PMID-
            record_positions = []
            for match in re.finditer(r"^PMID-", text_content, re.MULTILINE):
                record_positions.append(match.start())
            
            # Divide o texto nas posições encontradas
            for i in range(len(record_positions)):
                start = record_positions[i]
                end = record_positions[i + 1] if i + 1 < len(record_positions) else len(text_content)
                record = text_content[start:end].strip()
                if record:
                    records.append(record)
        
        return records
    
    def _detect_format(self, text_content: str) -> str:
        """Detecta o formato do arquivo TXT"""
        # Verifica formato citation-export (Record #X of Y)
        if re.search(r"Record #\d+ of \d+", text_content):
            return "citation_export"
            
        # Verifica formato records.txt (RECORD X, campos em maiúsculas)
        if re.search(r"RECORD \d+", text_content) and re.search(r"^TITLE\s*$", text_content, re.MULTILINE):
            return "records_format"
        
        # Verifica se usa terminador ER
        if re.search(r"\nER\s*\n", text_content):
            return "er_terminated"
        
        # Verifica se usa campos completos (Authors:, Title:, etc.)
        full_field_patterns = [
            r"(?i)^Authors?\s*:",
            r"(?i)^Title\s*:",
            r"(?i)^Year\s*:",
            r"(?i)^Abstract\s*:",
            r"(?i)^DOI\s*:"
        ]
        
        full_field_count = sum(1 for pattern in full_field_patterns 
                              if re.search(pattern, text_content, re.MULTILINE))
        
        if full_field_count >= 2:
            return "full_fields"
        
        # Padrão: formato PubMed
        return "pubmed"
    
    def _extract_txt_fields(self, record: str, format_type: str) -> Dict[str, Any]:
        """Extrai os campos necessários do registro TXT baseado no formato detectado"""
        article = {
            "Title": "Sem informação",
            "Authors": "Sem informação",
            "Year": "Sem informação", 
            "DOI": "Sem informação",
            "Abstract": "Sem informação"
        }
        
        if format_type == "citation_export":
            # Formato citation-export
            article = self._extract_citation_export_format(record)
        elif format_type == "records_format":
            # Formato records.txt
            article = self._extract_records_format(record)
        elif format_type == "full_fields":
            # Formato com campos completos (Authors:, Title:, etc.)
            article = self._extract_full_fields_format(record)
        elif format_type == "er_terminated":
            # Formato com tags de duas letras e terminador ER
            article = self._extract_er_terminated_format(record)
        else:
            # Formato PubMed padrão
            article = self._extract_pubmed_format(record)
        
        return article
    
    def _extract_citation_export_format(self, record: str) -> Dict[str, Any]:
        """Extrai campos do formato citation-export (citation-export.txt)"""
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
            if not line or line.startswith("Record #"):
                continue
            
            # Verifica se a linha começa com um identificador de campo
            field_match = re.match(r"^(ID|AU|TI|SO|YR|XR|PT|KY|AB|DOI|US):\s*(.*)$", line)
            
            if field_match:
                # Processa o campo anterior
                if current_field and current_content:
                    self._process_citation_export_field(article, current_field, " ".join(current_content))
                
                # Inicia novo campo
                current_field = field_match.group(1)
                current_content = [field_match.group(2)] if field_match.group(2) else []
            elif current_field:
                # Continuação do campo atual
                current_content.append(line)
        
        # Processa o último campo
        if current_field and current_content:
            self._process_citation_export_field(article, current_field, " ".join(current_content))
        
        return article
    
    def _extract_records_format(self, record: str) -> Dict[str, Any]:
        """Extrai campos do formato records.txt"""
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
            if not line.strip() or line.strip().startswith("RECORD "):
                continue
            
            # Verifica se a linha é um identificador de campo (em maiúsculas, sem indentação)
            if re.match(r"^(TITLE|AUTHOR NAMES|PUBLICATION YEAR|ABSTRACT|DOI)$", line.strip()):
                # Processa o campo anterior
                if current_field and current_content:
                    self._process_records_field(article, current_field, " ".join(current_content))
                
                # Inicia novo campo
                current_field = line.strip()
                current_content = []
            elif current_field and (line.startswith("  ") or line.startswith("\t")):
                # Continuação do campo atual (linhas indentadas)
                current_content.append(line.strip())
        
        # Processa o último campo
        if current_field and current_content:
            self._process_records_field(article, current_field, " ".join(current_content))
        
        return article
    
    def _extract_full_fields_format(self, record: str) -> Dict[str, Any]:
        """Extrai campos do formato de campos completos (records.txt)"""
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
            # Verifica se a linha começa com um campo conhecido
            field_match = re.match(r"(?i)^(Authors?|Title|Year|DOI|Abstract)\s*:\s*(.*)$", line)
            
            if field_match:
                # Processa o campo anterior
                if current_field and current_content:
                    self._process_full_field(article, current_field, " ".join(current_content))
                
                # Inicia novo campo
                current_field = field_match.group(1).lower()
                current_content = [field_match.group(2)] if field_match.group(2).strip() else []
            elif line.strip() and current_field:
                # Continuação do campo atual (linhas indentadas)
                if line.startswith("  ") or line.startswith("\t"):
                    current_content.append(line.strip())
        
        # Processa o último campo
        if current_field and current_content:
            self._process_full_field(article, current_field, " ".join(current_content))
        
        return article
    
    def _extract_er_terminated_format(self, record: str) -> Dict[str, Any]:
        """Extrai campos do formato com terminador ER (citation-export.txt)"""
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
            if not line or line == "ER":
                continue
            
            # Verifica se a linha começa com um identificador de campo de duas letras
            field_match = re.match(r"^([A-Z]{2})\s*-?\s*(.*)$", line)
            
            if field_match:
                # Processa o campo anterior
                if current_field and current_content:
                    self._process_er_field(article, current_field, " ".join(current_content))
                
                # Inicia novo campo
                current_field = field_match.group(1)
                current_content = [field_match.group(2)] if field_match.group(2) else []
            elif current_field and (line.startswith("  ") or line.startswith("\t")):
                # Continuação do campo atual (linhas indentadas)
                current_content.append(line)
        
        # Processa o último campo
        if current_field and current_content:
            self._process_er_field(article, current_field, " ".join(current_content))
        
        return article
    
    def _extract_pubmed_format(self, record: str) -> Dict[str, Any]:
        """Extrai campos do formato PubMed padrão"""
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
                    self._process_pubmed_field(article, current_field, " ".join(current_content))
                
                # Inicia novo campo
                current_field = field_match.group(1)
                current_content = [field_match.group(2)] if field_match.group(2) else []
            else:
                # Continuação do campo atual
                if current_field:
                    current_content.append(line)
        
        # Processa o último campo
        if current_field and current_content:
            self._process_pubmed_field(article, current_field, " ".join(current_content))
        
        return article
    
    def _process_citation_export_field(self, article: Dict[str, Any], field_code: str, content: str):
        """Processa campo do formato citation-export"""
        content = content.strip()
        if not content:
            return
        
        if field_code == "TI":
            article["Title"] = content
        elif field_code == "AU":
            if article["Authors"] == "Sem informação":
                article["Authors"] = content
            else:
                article["Authors"] += ", " + content
        elif field_code == "YR":
            year_match = re.search(r"\b(19|20)\d{2}\b", content)
            if year_match:
                article["Year"] = year_match.group()
            elif content.isdigit() and len(content) == 4:
                article["Year"] = content
        elif field_code == "DOI":
            doi_cleaned = self._clean_doi(content)
            if doi_cleaned:
                article["DOI"] = doi_cleaned
        elif field_code == "AB":
            abstract_cleaned = self._clean_abstract(content)
            if abstract_cleaned:
                article["Abstract"] = abstract_cleaned
    
    def _process_records_field(self, article: Dict[str, Any], field_name: str, content: str):
        """Processa campo do formato records.txt"""
        content = content.strip()
        if not content:
            return
        
        if field_name == "TITLE":
            article["Title"] = content
        elif field_name == "AUTHOR NAMES":
            article["Authors"] = content
        elif field_name == "PUBLICATION YEAR":
            year_match = re.search(r"\b(19|20)\d{2}\b", content)
            if year_match:
                article["Year"] = year_match.group()
            elif content.isdigit() and len(content) == 4:
                article["Year"] = content
        elif field_name == "DOI":
            doi_cleaned = self._clean_doi(content)
            if doi_cleaned:
                article["DOI"] = doi_cleaned
        elif field_name == "ABSTRACT":
            abstract_cleaned = self._clean_abstract(content)
            if abstract_cleaned:
                article["Abstract"] = abstract_cleaned
    
    def _process_full_field(self, article: Dict[str, Any], field_name: str, content: str):
        """Processa campo do formato de campos completos"""
        content = content.strip()
        if not content:
            return
        
        field_name = field_name.lower()
        
        if field_name in ["title"]:
            article["Title"] = content
        elif field_name in ["authors", "author"]:
            article["Authors"] = content
        elif field_name == "year":
            # Extrai ano se for uma string mais longa
            year_match = re.search(r"\b(19|20)\d{2}\b", content)
            if year_match:
                article["Year"] = year_match.group()
            elif content.isdigit() and len(content) == 4:
                article["Year"] = content
        elif field_name == "doi":
            doi_cleaned = self._clean_doi(content)
            if doi_cleaned:
                article["DOI"] = doi_cleaned
        elif field_name == "abstract":
            abstract_cleaned = self._clean_abstract(content)
            if abstract_cleaned:
                article["Abstract"] = abstract_cleaned
    
    def _process_er_field(self, article: Dict[str, Any], field_code: str, content: str):
        """Processa campo do formato com terminador ER"""
        content = content.strip()
        if not content:
            return
        
        # Mapeamento de códigos comuns
        if field_code == "TI":
            article["Title"] = content
        elif field_code in ["AU", "A1", "A2"]:
            if article["Authors"] == "Sem informação":
                article["Authors"] = content
            else:
                article["Authors"] += ", " + content
        elif field_code in ["PY", "Y1"]:
            year_match = re.search(r"\b(19|20)\d{2}\b", content)
            if year_match:
                article["Year"] = year_match.group()
        elif field_code in ["DI", "DO"]:
            doi_cleaned = self._clean_doi(content)
            if doi_cleaned:
                article["DOI"] = doi_cleaned
        elif field_code == "AB":
            abstract_cleaned = self._clean_abstract(content)
            if abstract_cleaned:
                article["Abstract"] = abstract_cleaned
    
    def _process_pubmed_field(self, article: Dict[str, Any], field_code: str, content: str):
        """Processa campo do formato PubMed"""
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
            abstract_cleaned = self._clean_abstract(content)
            if abstract_cleaned:
                article["Abstract"] = abstract_cleaned
        
        # DOI (procura por tag [doi])
        elif field_code in ["AID", "LID"]:
            doi_match = re.search(r"(.+?)\s*\[doi\]", content, re.IGNORECASE)
            if doi_match:
                doi_raw = doi_match.group(1).strip()
                doi_cleaned = self._clean_doi(doi_raw)
                if doi_cleaned:
                    article["DOI"] = doi_cleaned
    
    def _clean_doi(self, doi: str) -> Optional[str]:
        """Limpa e valida o formato do DOI"""
        if not doi:
            return None
            
        # Remove prefixos comuns e espaços
        doi = doi.replace("doi:", "").replace("DOI:", "").strip()
        doi = doi.replace("https://doi.org/", "").replace("http://dx.doi.org/", "")
        doi = doi.rstrip(".,;")
        
        # Valida formato básico do DOI
        if re.match(r"^10\.\d+/.+", doi):
            return doi
            
        return None
    
    def _clean_abstract(self, abstract: str) -> Optional[str]:
        """Limpa e formata o resumo"""
        if not abstract:
            return None
            
        # Remove tags HTML se presentes
        abstract = re.sub(r"<[^>]+>", "", abstract)
        
        # Remove espaços em branco extras e quebras de linha desnecessárias
        abstract = " ".join(abstract.split())
        
        # Remove caracteres não imprimíveis
        abstract = "".join(char for char in abstract if char.isprintable() or char.isspace())
        
        abstract = abstract.strip()
        
        # Verifica se o resumo tem conteúdo útil (mais de 10 caracteres)
        if len(abstract) > 10:
            return abstract
            
        return None
