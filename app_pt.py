import streamlit as st
import pandas as pd
import io
import re
from typing import List, Dict, Any
# Importa as versões traduzidas dos módulos
from parsers_pt import RISParser, TXTParser
from utils_pt import create_excel_file, validate_files
from abstract_fetcher import AbstractFetcher
from duplicate_remover import DuplicateRemover

def main():
    st.title("📚 Parser de Base de Dados Bibliográfica")
    st.markdown("Faça upload de múltiplos arquivos .ris e .txt das bases de dados Lilacs, Embase, Cochrane e PubMed para gerar uma planilha Excel unificada.")
    
    # Uploader de arquivos
    uploaded_files = st.file_uploader(
        "Escolha os arquivos bibliográficos",
        type=["ris", "txt"],
        accept_multiple_files=True,
        help="Faça upload de arquivos .ris ou .txt (formato PubMed) de diversas bases de dados"
    )
    
    if uploaded_files:
        st.success(f"📁 {len(uploaded_files)} arquivo(s) carregado(s) com sucesso!")
        
        # Valida os arquivos
        valid_files, invalid_files = validate_files(uploaded_files)
        
        if invalid_files:
            st.warning(f"⚠️ {len(invalid_files)} arquivo(s) não puderam ser processados: {', '.join(invalid_files)}")
        
        if valid_files:
            # Opções de processamento
            st.subheader("🔧 Opções de Processamento")
            
            col1, col2 = st.columns(2)
            
            with col1:
                fetch_abstracts = st.checkbox(
                    "🔍 Buscar resumos automaticamente",
                    value=True,
                    help="Tenta buscar resumos faltantes usando DOI via CrossRef e PubMed"
                )
            
            with col2:
                remove_duplicates = st.checkbox(
                    "🗑️ Remover duplicatas",
                    value=True,
                    help="Remove artigos duplicados baseado em título e DOI"
                )
            
            # Botão para processar arquivos
            if st.button("🔄 Processar Arquivos", type="primary"):
                process_files(valid_files, fetch_abstracts, remove_duplicates)
        else:
            st.error("❌ Nenhum arquivo válido para processar. Por favor, faça upload de arquivos .ris ou .txt.")

def process_files(files: List[Any], fetch_abstracts: bool, remove_duplicates: bool):
    """Processa os arquivos enviados e gera a saída em Excel"""
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    all_articles = []
    total_files = len(files)
    
    # Etapa 1: Processar arquivos
    status_text.text("📄 Processando arquivos bibliográficos...")
    
    for i, file in enumerate(files):
        status_text.text(f"📄 Processando {file.name}... ({i+1}/{total_files})")
        progress_bar.progress((i + 1) / total_files * 0.4)  # 40% para processamento de arquivos
        
        try:
            # Lê o conteúdo do arquivo
            file_content = file.read()
            
            # Detecta o formato do arquivo e analisa
            if file.name.lower().endswith(".ris"):
                parser = RISParser()
                articles = parser.parse(file_content)
            elif file.name.lower().endswith(".txt"):
                parser = TXTParser()
                articles = parser.parse(file_content)
            else:
                st.warning(f"⚠️ Formato de arquivo não suportado: {file.name}")
                continue
            
            # Adiciona informação do arquivo de origem a cada artigo
            for article in articles:
                article["source_file"] = file.name
            
            all_articles.extend(articles)
            
        except Exception as e:
            st.error(f"❌ Erro ao processar {file.name}: {str(e)}")
            continue
    
    if not all_articles:
        st.error("❌ Nenhum artigo pôde ser extraído dos arquivos enviados. Por favor, verifique os formatos e o conteúdo dos arquivos.")
        return
    
    # Cria o DataFrame inicial
    df = pd.DataFrame(all_articles)
    
    # Garante que todas as colunas necessárias existam
    required_columns = ["Title", "Authors", "Year", "DOI", "Abstract"]
    for col in required_columns:
        if col not in df.columns:
            df[col] = "Sem informação"
        else:
            df[col] = df[col].replace([None, '', 'No information'], 'Sem informação')
    
    original_count = len(df)
    
    # Etapa 2: Buscar resumos (se habilitado)
    fetched_abstracts = 0
    if fetch_abstracts:
        status_text.text("🔍 Buscando resumos faltantes...")
        progress_bar.progress(0.5)  # 50%
        
        fetcher = AbstractFetcher()
        
        # Conta quantos artigos precisam de resumo
        missing_abstract_mask = (df["Abstract"] == "Sem informação") & (df["DOI"] != "Sem informação")
        articles_needing_abstract = df[missing_abstract_mask]
        total_to_fetch = len(articles_needing_abstract)
        
        if total_to_fetch > 0:
            st.info(f"🔍 Buscando resumos para {total_to_fetch} artigos...")
            
            # Criar uma barra de progresso separada para busca de resumos
            abstract_progress = st.progress(0)
            abstract_status = st.empty()
            
            def update_abstract_progress(current, total, current_doi):
                abstract_progress.progress(current / total if total > 0 else 0)
                abstract_status.text(f"Buscando resumo {current + 1}/{total}: {current_doi[:50]}...")
            
            df, fetched_abstracts = fetcher.fetch_abstracts_batch(df, update_abstract_progress)
            
            abstract_progress.empty()
            abstract_status.empty()
            
            if fetched_abstracts > 0:
                st.success(f"✅ {fetched_abstracts} resumos encontrados e adicionados!")
            else:
                st.info("ℹ️ Nenhum resumo adicional foi encontrado.")
    
    progress_bar.progress(0.7)  # 70%
    
    # Etapa 3: Remover duplicatas (se habilitado)
    duplicates_info = []
    if remove_duplicates:
        status_text.text("🗑️ Removendo duplicatas...")
        progress_bar.progress(0.8)  # 80%
        
        duplicate_remover = DuplicateRemover()
        df, duplicates_info = duplicate_remover.remove_duplicates(df)
        
        if duplicates_info:
            st.success(f"✅ {len(duplicates_info)} duplicatas removidas!")
        else:
            st.info("ℹ️ Nenhuma duplicata encontrada.")
    
    # Reordena as colunas
    df = df[required_columns + [col for col in df.columns if col not in required_columns]]
    
    progress_bar.progress(1.0)  # 100%
    status_text.text("✅ Processamento concluído!")
    
    # Exibe estatísticas finais
    final_count = len(df)
    
    st.success(f"✅ Processamento concluído!")
    
    # Métricas de resumo
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Artigos Originais", original_count)
    with col2:
        st.metric("Artigos Finais", final_count)
    with col3:
        st.metric("Resumos Encontrados", fetched_abstracts)
    with col4:
        st.metric("Duplicatas Removidas", len(duplicates_info))
    
    # Seção de preview expandida
    st.subheader("📋 Pré-visualização dos Artigos")
    
    # Controles de paginação
    articles_per_page = st.selectbox("Artigos por página:", [10, 25, 50, 100], index=1)
    
    total_pages = (len(df) - 1) // articles_per_page + 1 if len(df) > 0 else 1
    
    if total_pages > 1:
        page = st.selectbox(f"Página (1-{total_pages}):", range(1, total_pages + 1))
        start_idx = (page - 1) * articles_per_page
        end_idx = min(start_idx + articles_per_page, len(df))
        
        st.write(f"Mostrando artigos {start_idx + 1}-{end_idx} de {len(df)}")
        preview_df = df.iloc[start_idx:end_idx][required_columns]
    else:
        preview_df = df[required_columns]
    
    st.dataframe(preview_df, use_container_width=True)
    
    # Informações sobre duplicatas removidas
    if duplicates_info:
        with st.expander(f"🗑️ Duplicatas Removidas ({len(duplicates_info)})"):
            st.write("**Artigos que foram identificados como duplicatas e removidos:**")
            
            duplicates_df = pd.DataFrame([
                {
                    "Título": info["title"][:100] + "..." if len(info["title"]) > 100 else info["title"],
                    "Autores": info["authors"][:50] + "..." if len(info["authors"]) > 50 else info["authors"],
                    "Ano": info["year"],
                    "DOI": info["doi"],
                    "Arquivo Origem": info["source_file"],
                    "Motivo da Remoção": info["reason"]
                }
                for info in duplicates_info
            ])
            
            st.dataframe(duplicates_df, use_container_width=True)
    
    # Seção de download
    st.subheader("💾 Baixar Resultados")
    
    # Cria o arquivo Excel
    excel_buffer = create_excel_file(df)
    
    st.download_button(
        label="📥 Baixar Arquivo Excel",
        data=excel_buffer,
        file_name="dados_bibliograficos.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        type="primary"
    )
    
    # Estatísticas detalhadas
    with st.expander("📊 Estatísticas Detalhadas"):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Total de Artigos", len(df))
            articles_with_title = len(df[df["Title"] != "Sem informação"])
            st.metric("Artigos com Título", articles_with_title)
            
        with col2:
            articles_with_doi = len(df[df["DOI"] != "Sem informação"])
            st.metric("Artigos com DOI", articles_with_doi)
            articles_with_authors = len(df[df["Authors"] != "Sem informação"])
            st.metric("Artigos com Autores", articles_with_authors)
            
        with col3:
            articles_with_abstract = len(df[df["Abstract"] != "Sem informação"])
            st.metric("Artigos com Resumo", articles_with_abstract)
            articles_with_year = len(df[df["Year"] != "Sem informação"])
            st.metric("Artigos com Ano", articles_with_year)
        
        # Gráfico de completude dos dados
        st.subheader("📈 Completude dos Dados")
        completeness_data = {
            "Campo": ["Título", "Autores", "Ano", "DOI", "Resumo"],
            "Artigos Completos": [
                len(df[df["Title"] != "Sem informação"]),
                len(df[df["Authors"] != "Sem informação"]),
                len(df[df["Year"] != "Sem informação"]),
                len(df[df["DOI"] != "Sem informação"]),
                len(df[df["Abstract"] != "Sem informação"])
            ]
        }
        completeness_df = pd.DataFrame(completeness_data)
        st.bar_chart(completeness_df.set_index("Campo"))
        
        # Detalhamento por arquivo
        st.subheader("📁 Detalhamento por Arquivo")
        if "source_file" in df.columns:
            file_counts = df["source_file"].value_counts()
            st.bar_chart(file_counts)
            
            # Tabela detalhada por arquivo
            file_details = []
            for filename in file_counts.index:
                file_df = df[df["source_file"] == filename]
                file_details.append({
                    "Arquivo": filename,
                    "Total Artigos": len(file_df),
                    "Com Resumo": len(file_df[file_df["Abstract"] != "Sem informação"]),
                    "Com DOI": len(file_df[file_df["DOI"] != "Sem informação"]),
                    "Completude (%)": round((len(file_df[file_df["Abstract"] != "Sem informação"]) / len(file_df)) * 100, 1)
                })
            
            file_details_df = pd.DataFrame(file_details)
            st.dataframe(file_details_df, use_container_width=True)

if __name__ == "__main__":
    main()
