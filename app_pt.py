import streamlit as st
import pandas as pd
import io
import re
from typing import List, Dict, Any
# Importa as versões traduzidas dos módulos
from parsers_pt import RISParser, TXTParser
from utils_pt import create_excel_file, validate_files

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
            # Botão para processar arquivos
            if st.button("🔄 Processar Arquivos", type="primary"):
                process_files(valid_files)
        else:
            st.error("❌ Nenhum arquivo válido para processar. Por favor, faça upload de arquivos .ris ou .txt.")

def process_files(files: List[Any]):
    """Processa os arquivos enviados e gera a saída em Excel"""
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    all_articles = []
    total_files = len(files)
    
    for i, file in enumerate(files):
        status_text.text(f"Processando {file.name}...")
        progress_bar.progress((i + 1) / total_files)
        
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
    
    status_text.text("Processamento concluído!")
    
    if all_articles:
        # Cria o DataFrame
        df = pd.DataFrame(all_articles)
        
        # Garante que todas as colunas necessárias existam
        required_columns = ["Title", "Authors", "Year", "DOI", "Abstract"]
        for col in required_columns:
            if col not in df.columns:
                df[col] = "Sem informação" # Padroniza para 'Sem informação'
            else:
                 # Garante que valores vazios ou 'No information' sejam padronizados
                 df[col] = df[col].replace([None, '', 'No information'], 'Sem informação')
        
        # Reordena as colunas
        df = df[required_columns + [col for col in df.columns if col not in required_columns]]
        
        # Exibe estatísticas
        st.success(f"✅ {len(all_articles)} artigos processados com sucesso de {len(files)} arquivos!")
        
        # Mostra pré-visualização
        st.subheader("📋 Pré-visualização (Primeiros 10 Artigos)")
        preview_df = df.head(10)[required_columns]
        st.dataframe(preview_df, use_container_width=True)
        
        # Seção de download
        st.subheader("💾 Baixar Resultados")
        
        # Cria o arquivo Excel
        excel_buffer = create_excel_file(df)
        
        st.download_button(
            label="📥 Baixar Arquivo Excel",
            data=excel_buffer,
            file_name="dados_bibliograficos.xlsx", # Nome do arquivo traduzido
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            type="primary"
        )
        
        # Estatísticas adicionais
        with st.expander("📊 Estatísticas Detalhadas"):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Total de Artigos", len(df))
                
            with col2:
                articles_with_doi = len(df[df["DOI"] != "Sem informação"])
                st.metric("Artigos com DOI", articles_with_doi)
                
            with col3:
                articles_with_abstract = len(df[df["Abstract"] != "Sem informação"])
                st.metric("Artigos com Resumo", articles_with_abstract)
            
            # Mostra detalhamento por arquivo
            st.subheader("Detalhamento por Arquivo")
            if "source_file" in df.columns:
                file_counts = df["source_file"].value_counts()
                st.bar_chart(file_counts)
    
    else:
        st.error("❌ Nenhum artigo pôde ser extraído dos arquivos enviados. Por favor, verifique os formatos e o conteúdo dos arquivos.")

if __name__ == "__main__":
    main()

