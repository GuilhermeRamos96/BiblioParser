import pandas as pd
import hashlib
import re
from typing import Tuple, List, Dict, Any
import streamlit as st

class DuplicateRemover:
    """Classe para remover duplicatas baseado em título e DOI"""
    
    def __init__(self):
        self.removed_articles = []
        self.removal_reasons = []
        
    def remove_duplicates(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, List[Dict[str, Any]]]:
        """
        Remove duplicatas baseado em título e DOI
        Preserva artigos com 'Sem informação' em título ou DOI
        """
        self.removed_articles = []
        self.removal_reasons = []
        
        if df.empty:
            return df, []
            
        # Cria identificadores únicos para cada artigo
        df = df.copy()
        df["_temp_id"] = range(len(df))
        
        # Agrupa artigos por critérios de duplicata
        duplicates_info = []
        processed_ids = set()
        
        for idx, row in df.iterrows():
            if idx in processed_ids:
                continue
                
            # Se título ou DOI é "Sem informação", não considera como duplicata
            if row["Title"] == "Sem informação" or row["DOI"] == "Sem informação":
                processed_ids.add(idx)
                continue
                
            # Busca duplicatas baseado em título e DOI
            title_matches = self._find_title_matches(df, row["Title"], processed_ids)
            doi_matches = self._find_doi_matches(df, row["DOI"], processed_ids)
            
            # Combina matches de título e DOI
            all_matches = list(set(title_matches + doi_matches + [idx]))
            
            if len(all_matches) > 1:
                # Seleciona o "melhor" artigo do grupo de duplicatas
                best_article_idx = self._select_best_article(df, all_matches)
                duplicates_to_remove = [i for i in all_matches if i != best_article_idx]
                
                # Registra informações sobre as duplicatas removidas
                for dup_idx in duplicates_to_remove:
                    duplicate_info = {
                        "original_index": dup_idx,
                        "title": df.at[dup_idx, "Title"],
                        "authors": df.at[dup_idx, "Authors"],
                        "year": df.at[dup_idx, "Year"],
                        "doi": df.at[dup_idx, "DOI"],
                        "source_file": df.at[dup_idx, "source_file"] if "source_file" in df.columns else "N/A",
                        "reason": self._get_duplicate_reason(df, dup_idx, best_article_idx),
                        "kept_article_index": best_article_idx
                    }
                    duplicates_info.append(duplicate_info)
                
                # Marca todos os matches como processados
                processed_ids.update(all_matches)
            else:
                processed_ids.add(idx)
        
        # Remove as duplicatas do DataFrame
        indices_to_remove = [info["original_index"] for info in duplicates_info]
        df_cleaned = df.drop(indices_to_remove).reset_index(drop=True)
        
        # Remove coluna temporária
        if "_temp_id" in df_cleaned.columns:
            df_cleaned = df_cleaned.drop("_temp_id", axis=1)
            
        return df_cleaned, duplicates_info
    
    def _find_title_matches(self, df: pd.DataFrame, title: str, processed_ids: set) -> List[int]:
        """Encontra artigos com títulos similares"""
        matches = []
        
        if title == "Sem informação":
            return matches
            
        normalized_title = self._normalize_title(title)
        
        for idx, row in df.iterrows():
            if idx in processed_ids:
                continue
                
            if row["Title"] == "Sem informação":
                continue
                
            other_normalized = self._normalize_title(row["Title"])
            
            # Verifica similaridade de título
            if self._titles_are_similar(normalized_title, other_normalized):
                matches.append(idx)
                
        return matches
    
    def _find_doi_matches(self, df: pd.DataFrame, doi: str, processed_ids: set) -> List[int]:
        """Encontra artigos com mesmo DOI"""
        matches = []
        
        if doi == "Sem informação":
            return matches
            
        normalized_doi = self._normalize_doi(doi)
        
        for idx, row in df.iterrows():
            if idx in processed_ids:
                continue
                
            if row["DOI"] == "Sem informação":
                continue
                
            other_normalized = self._normalize_doi(row["DOI"])
            
            if normalized_doi == other_normalized:
                matches.append(idx)
                
        return matches
    
    def _normalize_title(self, title: str) -> str:
        """Normaliza título para comparação"""
        if not title or title == "Sem informação":
            return ""
            
        # Remove pontuação, converte para minúsculas e remove espaços extras
        normalized = re.sub(r"[^\w\s]", "", title.lower())
        normalized = re.sub(r"\s+", " ", normalized).strip()
        
        return normalized
    
    def _normalize_doi(self, doi: str) -> str:
        """Normaliza DOI para comparação"""
        if not doi or doi == "Sem informação":
            return ""
            
        # Remove prefixos e normaliza formato
        normalized = doi.replace("doi:", "").replace("DOI:", "").strip()
        normalized = normalized.replace("https://doi.org/", "").replace("http://dx.doi.org/", "")
        
        return normalized.lower()
    
    def _titles_are_similar(self, title1: str, title2: str, threshold: float = 0.9) -> bool:
        """Verifica se dois títulos são similares usando similaridade de conjunto de palavras"""
        if not title1 or not title2:
            return False
            
        words1 = set(title1.split())
        words2 = set(title2.split())
        
        if len(words1) == 0 or len(words2) == 0:
            return False
            
        # Calcula similaridade de Jaccard
        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))
        
        similarity = intersection / union if union > 0 else 0
        
        return similarity >= threshold
    
    def _select_best_article(self, df: pd.DataFrame, duplicate_indices: List[int]) -> int:
        """Seleciona o melhor artigo de um grupo de duplicatas"""
        best_idx = duplicate_indices[0]
        best_score = 0
        
        for idx in duplicate_indices:
            score = self._calculate_article_quality_score(df.iloc[idx])
            
            if score > best_score:
                best_score = score
                best_idx = idx
                
        return best_idx
    
    def _calculate_article_quality_score(self, article: pd.Series) -> int:
        """Calcula pontuação de qualidade do artigo baseado em completude dos dados"""
        score = 0
        
        # Pontos por campo preenchido
        if article.get("Title", "Sem informação") != "Sem informação":
            score += 10
            
        if article.get("Authors", "Sem informação") != "Sem informação":
            score += 8
            
        if article.get("Year", "Sem informação") != "Sem informação":
            score += 5
            
        if article.get("DOI", "Sem informação") != "Sem informação":
            score += 15  # DOI tem peso maior
            
        if article.get("Abstract", "Sem informação") != "Sem informação":
            score += 20  # Resumo tem peso maior
            
        # Pontos extras por tamanho do resumo
        abstract = article.get("Abstract", "")
        if abstract and abstract != "Sem informação":
            if len(abstract) > 500:
                score += 5
            elif len(abstract) > 200:
                score += 3
                
        return score
    
    def _get_duplicate_reason(self, df: pd.DataFrame, removed_idx: int, kept_idx: int) -> str:
        """Gera razão para remoção da duplicata"""
        removed_article = df.iloc[removed_idx]
        kept_article = df.iloc[kept_idx]
        
        reasons = []
        
        # Verifica se há match por título
        if (removed_article["Title"] != "Sem informação" and 
            kept_article["Title"] != "Sem informação"):
            removed_title = self._normalize_title(removed_article["Title"])
            kept_title = self._normalize_title(kept_article["Title"])
            
            if self._titles_are_similar(removed_title, kept_title):
                reasons.append("título similar")
        
        # Verifica se há match por DOI
        if (removed_article["DOI"] != "Sem informação" and 
            kept_article["DOI"] != "Sem informação"):
            removed_doi = self._normalize_doi(removed_article["DOI"])
            kept_doi = self._normalize_doi(kept_article["DOI"])
            
            if removed_doi == kept_doi:
                reasons.append("mesmo DOI")
        
        if not reasons:
            reasons.append("critérios de duplicata")
            
        # Adiciona informação sobre qualidade
        removed_score = self._calculate_article_quality_score(removed_article)
        kept_score = self._calculate_article_quality_score(kept_article)
        
        quality_info = f"(pontuação: {removed_score} vs {kept_score} do artigo mantido)"
        
        return f"{', '.join(reasons)} {quality_info}"
