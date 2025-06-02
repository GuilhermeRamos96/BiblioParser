import requests
import time
import re
from typing import Optional, Dict, Any
import streamlit as st

class AbstractFetcher:
    """Classe para buscar resumos automaticamente usando DOI"""
    
    def __init__(self):
        self.crossref_base_url = "https://api.crossref.org/works/"
        self.pubmed_base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
        self.request_timeout = 10
        self.retry_attempts = 3
        self.rate_limit_delay = 0.5  # Delay entre requisições em segundos
        
    def fetch_abstract(self, doi: str) -> Optional[str]:
        """
        Busca o resumo usando o DOI fornecido
        Tenta primeiro CrossRef, depois PubMed
        """
        if not doi or doi == "Sem informação":
            return None
            
        # Limpa o DOI
        clean_doi = self._clean_doi(doi)
        if not clean_doi:
            return None
            
        # Tenta buscar no CrossRef primeiro
        abstract = self._fetch_from_crossref(clean_doi)
        if abstract:
            return abstract
            
        # Se não encontrar no CrossRef, tenta no PubMed
        abstract = self._fetch_from_pubmed(clean_doi)
        return abstract
    
    def _clean_doi(self, doi: str) -> Optional[str]:
        """Limpa e valida o formato do DOI"""
        if not doi:
            return None
            
        # Remove prefixos comuns e espaços
        doi = doi.replace("doi:", "").replace("DOI:", "").strip()
        doi = doi.replace("https://doi.org/", "").replace("http://dx.doi.org/", "")
        
        # Valida formato básico do DOI
        if re.match(r"^10\.\d+/.+", doi):
            return doi
            
        return None
    
    def _fetch_from_crossref(self, doi: str) -> Optional[str]:
        """Busca resumo no CrossRef"""
        try:
            url = f"{self.crossref_base_url}{doi}"
            headers = {
                "User-Agent": "BiblioParser/1.0 (mailto:researcher@example.com)"
            }
            
            for attempt in range(self.retry_attempts):
                try:
                    response = requests.get(url, headers=headers, timeout=self.request_timeout)
                    
                    if response.status_code == 200:
                        data = response.json()
                        
                        # Extrai o resumo se disponível
                        message = data.get("message", {})
                        abstract = message.get("abstract")
                        
                        if abstract:
                            # Remove tags HTML se presentes
                            abstract = re.sub(r"<[^>]+>", "", abstract)
                            return abstract.strip()
                            
                    elif response.status_code == 429:  # Rate limited
                        time.sleep(2 ** attempt)  # Backoff exponencial
                        continue
                        
                except requests.RequestException:
                    if attempt < self.retry_attempts - 1:
                        time.sleep(1)
                        continue
                    
            # Rate limiting entre requisições
            time.sleep(self.rate_limit_delay)
            
        except Exception as e:
            st.write(f"Erro ao buscar no CrossRef para DOI {doi}: {str(e)}")
            
        return None
    
    def _fetch_from_pubmed(self, doi: str) -> Optional[str]:
        """Busca resumo no PubMed usando DOI"""
        try:
            # Primeiro, busca o PMID usando o DOI
            pmid = self._get_pmid_from_doi(doi)
            if not pmid:
                return None
                
            # Depois busca o resumo usando o PMID
            return self._fetch_abstract_from_pmid(pmid)
            
        except Exception as e:
            st.write(f"Erro ao buscar no PubMed para DOI {doi}: {str(e)}")
            
        return None
    
    def _get_pmid_from_doi(self, doi: str) -> Optional[str]:
        """Obtém PMID usando DOI no PubMed"""
        try:
            search_url = f"{self.pubmed_base_url}esearch.fcgi"
            params = {
                "db": "pubmed",
                "term": f"{doi}[doi]",
                "retmode": "json",
                "retmax": 1
            }
            
            response = requests.get(search_url, params=params, timeout=self.request_timeout)
            
            if response.status_code == 200:
                data = response.json()
                id_list = data.get("esearchresult", {}).get("idlist", [])
                
                if id_list:
                    return id_list[0]
                    
            time.sleep(self.rate_limit_delay)
            
        except Exception:
            pass
            
        return None
    
    def _fetch_abstract_from_pmid(self, pmid: str) -> Optional[str]:
        """Busca resumo usando PMID"""
        try:
            fetch_url = f"{self.pubmed_base_url}efetch.fcgi"
            params = {
                "db": "pubmed",
                "id": pmid,
                "retmode": "xml",
                "rettype": "abstract"
            }
            
            response = requests.get(fetch_url, params=params, timeout=self.request_timeout)
            
            if response.status_code == 200:
                # Extrai texto do resumo do XML
                xml_content = response.text
                
                # Busca pelo resumo no XML
                abstract_match = re.search(
                    r"<AbstractText[^>]*>(.*?)</AbstractText>", 
                    xml_content, 
                    re.DOTALL | re.IGNORECASE
                )
                
                if abstract_match:
                    abstract = abstract_match.group(1)
                    # Remove tags HTML restantes
                    abstract = re.sub(r"<[^>]+>", "", abstract)
                    return abstract.strip()
                    
            time.sleep(self.rate_limit_delay)
            
        except Exception:
            pass
            
        return None
    
    def fetch_abstracts_batch(self, articles_df, progress_callback=None):
        """
        Busca resumos em lote para artigos que não possuem resumo
        """
        missing_abstract_mask = articles_df["Abstract"] == "Sem informação"
        articles_needing_abstract = articles_df[missing_abstract_mask & (articles_df["DOI"] != "Sem informação")]
        
        total_to_fetch = len(articles_needing_abstract)
        fetched_count = 0
        
        if total_to_fetch == 0:
            return articles_df, 0
            
        for idx, row in articles_needing_abstract.iterrows():
            doi = row["DOI"]
            
            if progress_callback:
                progress_callback(fetched_count, total_to_fetch, doi)
                
            abstract = self.fetch_abstract(doi)
            
            if abstract:
                articles_df.at[idx, "Abstract"] = abstract
                fetched_count += 1
                
        return articles_df, fetched_count
