import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import numpy as np

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(
    page_title="Minha Biblioteca Musical",
    page_icon="🎵",
    layout="wide"
)

# --- FUNÇÕES AUXILIARES ---

def get_color_for_rating(rating):
    """Retorna uma cor com base na nota média."""
    if rating < 5:
        return "red"
    elif rating < 6:
        return "orange"
    elif rating < 7:
        return "gray"
    elif rating < 8.5:
        return "blue"
    elif rating < 9.5:
        return "green"
    else:
        return "violet"

def get_rating_label(rating):
    """Retorna um rótulo textual para a nota."""
    if rating < 5:
        return "Péssimo"
    elif rating < 6:
        return "Ruim"
    elif rating < 7:
        return "Regular"
    elif rating < 8.5:
        return "Bom"
    elif rating < 9.5:
        return "Ótimo"
    else:
        return "Excelente"

def format_list_to_string(data_list):
    """Converte uma lista em uma string separada por '; '."""
    return '; '.join(map(str, data_list))

def format_string_to_list(data_string):
    """Converte uma string separada por ';' em uma lista."""
    if isinstance(data_string, str):
        return [item.strip() for item in data_string.split(';')]
    return []

# --- TELA DE LOGIN ---
if 'user' not in st.session_state:
    st.session_state.user = None

if st.session_state.user is None:
    st.title("Bem-vindo à sua Biblioteca Musical 🎵")
    st.subheader("Por favor, selecione seu usuário para continuar")
    
    user_login = st.selectbox("Selecione o usuário:", ["", "jom", "jov", "job"])
    
    if st.button("Entrar"):
        if user_login:
            st.session_state.user = user_login
            st.rerun()
        else:
            st.error("Por favor, selecione um usuário.")
    st.stop()

# --- INICIALIZAÇÃO DO APP APÓS LOGIN ---
st.sidebar.title(f"Olá, {st.session_state.user.upper()}!")
if st.sidebar.button("Logout"):
    for key in st.session_state.keys():
        del st.session_state[key]
    st.rerun()

# --- CONEXÃO COM GOOGLE SHEETS E CARREGAMENTO DOS DADOS ---
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    df = conn.read(worksheet="Musicas", usecols=list(range(9)), ttl=5)
    df = df.dropna(how="all") # Remove linhas completamente vazias

    # Garante que as colunas de avaliação existam
    for u in ["jom", "jov", "job"]:
        col_name = f"rating_{u}"
        if col_name not in df.columns:
            df[col_name] = np.nan

    # Conversão de tipos e tratamento de dados
    df['trackNumber'] = pd.to_numeric(df['trackNumber'], errors='coerce')
    df['year'] = pd.to_numeric(df['year'], errors='coerce')
    for u in ["jom", "jov", "job"]:
        df[f"rating_{u}"] = pd.to_numeric(df[f"rating_{u}"], errors='coerce')

    # Armazena o dataframe no estado da sessão para evitar recarregamentos
    st.session_state.df = df

except Exception as e:
    st.error(f"Não foi possível conectar ao Google Sheets. Verifique a configuração e o nome da planilha/aba. Erro: {e}")
    st.stop()

df = st.session_state.df
USER_RATING_COL = f"rating_{st.session_state.user}"

# --- INTERFACE PRINCIPAL COM ABAS ---
st.title("🎵 Minha Biblioteca Musical")

# --- LÓGICA DE EDIÇÃO DE ÁLBUM (MODAL) ---
if 'editing_album' in st.session_state and st.session_state.editing_album:
    album_to_edit, artist_to_edit = st.session_state.editing_album
    
    st.header(f"✏️ Editando Álbum: {album_to_edit} - {artist_to_edit}")

    album_df = df[(df['album'] == album_to_edit) & (df['artists'] == artist_to_edit)].copy()
    album_df = album_df.sort_values(by='trackNumber').reset_index()

    with st.form("edit_album_form"):
        st.subheader("Informações do Álbum")
        
        # Converte a string de artistas para uma lista para o multiselect
        current_artists_list = format_string_to_list(album_df['artists'].iloc[0])
        all_artists = sorted(list(set(item for sublist in df['artists'].dropna().apply(format_string_to_list) for item in sublist)))
        
        edited_artists = st.multiselect(
            "Artistas", 
            options=all_artists, 
            default=current_artists_list
        )
        
        edited_album_title = st.text_input("Título do Álbum", value=album_df['album'].iloc[0])
        edited_year = st.number_input("Ano", value=int(album_df['year'].iloc[0]), min_value=1900, max_value=2100)

        st.subheader("Faixas")
        
        edited_tracks = []
        for index, row in album_df.iterrows():
            st.markdown(f"---")
            cols = st.columns([1, 4, 4, 2])
            
            new_track_number = cols[0].number_input("Nº", value=int(row['trackNumber']), key=f"num_{index}", min_value=1)
            new_title = cols[1].text_input("Título da Faixa", value=row['title'], key=f"title_{index}")
            
            current_composers_list = format_string_to_list(row['composers'])
            all_composers = sorted(list(set(item for sublist in df['composers'].dropna().apply(format_string_to_list) for item in sublist)))
            new_composers = cols[2].multiselect("Compositores", options=all_composers, default=current_composers_list, key=f"comp_{index}")
            
            # Lógica de avaliação
            ratings = {}
            for u in ["jom", "jov", "job"]:
                rating_col = f"rating_{u}"
                is_current_user = (u == st.session_state.user)
                current_rating = row[rating_col] if pd.notna(row[rating_col]) else 0.0
                
                # Usuário logado pode editar, outros apenas visualizam
                if is_current_user:
                    ratings[rating_col] = cols[3].number_input(f"Nota ({u.upper()})", value=current_rating, min_value=0.0, max_value=10.0, step=0.5, key=f"rating_{u}_{index}")
                else:
                    cols[3].metric(f"Nota ({u.upper()})", f"{current_rating:.1f}")
                    ratings[rating_col] = current_rating

            track_data = {
                'trackNumber': new_track_number,
                'title': new_title,
                'composers': format_list_to_string(new_composers),
                **ratings
            }
            edited_tracks.append(track_data)

        submitted = st.form_submit_button("Salvar Alterações")
        if submitted:
            # Atualiza o DataFrame principal
            original_indices = df[(df['album'] == album_to_edit) & (df['artists'] == artist_to_edit)].index
            df.drop(original_indices, inplace=True)

            new_rows = []
            for track in edited_tracks:
                new_row = {
                    'trackNumber': track['trackNumber'],
                    'title': track['title'],
                    'artists': format_list_to_string(edited_artists),
                    'album': edited_album_title,
                    'year': edited_year,
                    'composers': track['composers'],
                    'rating_jom': track['rating_jom'],
                    'rating_jov': track['rating_jov'],
                    'rating_job': track['rating_job']
                }
                new_rows.append(new_row)
            
            new_df = pd.DataFrame(new_rows)
            df_updated = pd.concat([df, new_df], ignore_index=True)
            
            # Atualiza o Google Sheets
            conn.update(worksheet="Musicas", data=df_updated)
            
            st.success(f"Álbum '{edited_album_title}' atualizado com sucesso!")
            st.session_state.editing_album = None
            st.rerun()

    if st.button("Cancelar Edição"):
        st.session_state.editing_album = None
        st.rerun()
    
    st.stop()


# --- ABAS DA APLICAÇÃO ---
tab1, tab2, tab3, tab4 = st.tabs([
    "📚 Minha Biblioteca", 
    "➕ Adicionar Dados", 
    "🎧 Próximos a Ouvir", 
    "🏆 Álbuns Concluídos"
])

with tab1:
    st.header("Explore sua coleção")

    # Filtros
    col1, col2 = st.columns(2)
    with col1:
        # Extrai todos os artistas únicos, lidando com múltiplos artistas por entrada
        all_artists_flat = sorted(list(set(item for sublist in df['artists'].dropna().apply(format_string_to_list) for item in sublist)))
        selected_artists = st.multiselect("Filtrar por Artista(s)", options=all_artists_flat)

    filtered_df = df.copy()
    if selected_artists:
        # Filtra o DF para conter apenas entradas que tenham PELO MENOS UM dos artistas selecionados
        filtered_df = df[df['artists'].apply(lambda x: any(artist in format_string_to_list(x) for artist in selected_artists))]

    with col2:
        if selected_artists:
            # Se artistas foram selecionados, mostra apenas álbuns desses artistas
            available_albums = sorted(filtered_df['album'].dropna().unique())
        else:
            # Senão, mostra todos os álbuns
            available_albums = sorted(df['album'].dropna().unique())
        
        selected_albums = st.multiselect("Filtrar por Álbum(ns)", options=available_albums)

    if selected_albums:
        filtered_df = filtered_df[filtered_df['album'].isin(selected_albums)]

    st.dataframe(filtered_df, use_container_width=True)

    # Dados consolidados
    if not filtered_df.empty:
        st.subheader("Média de Avaliações (Filtro Atual)")
        avg_cols = st.columns(3)
        for i, u in enumerate(["jom", "jov", "job"]):
            avg_rating = filtered_df[f'rating_{u}'].mean()
            with avg_cols[i]:
                st.metric(f"Média {u.upper()}", f"{avg_rating:.2f}" if pd.notna(avg_rating) else "N/A")

with tab2:
    st.header("Adicionar Novas Músicas ou Álbuns")

    add_type = st.radio("O que você deseja adicionar?", ("Álbum Inteiro", "Música Avulsa"), horizontal=True)

    if add_type == "Álbum Inteiro":
        with st.form("add_album_form", clear_on_submit=True):
            st.subheader("Informações do Álbum")
            
            # Lógica para artistas
            all_artists_flat = sorted(list(set(item for sublist in df['artists'].dropna().apply(format_string_to_list) for item in sublist)))
            album_artists = st.multiselect(
                "Artista(s) do Álbum", 
                options=all_artists_flat,
                help="Selecione artistas existentes ou digite novos nomes e pressione Enter."
            )
            new_artist_input = st.text_input("Adicionar novo artista (opcional)", help="Digite um novo nome e adicione na seleção acima.")
            
            album_title = st.text_input("Título do Álbum")
            album_year = st.number_input("Ano do Álbum", min_value=1900, max_value=2100, step=1)
            
            st.subheader("Faixas do Álbum")
            st.markdown("Insira o título e os compositores de cada faixa. O número da faixa será definido pela ordem de inserção.")
            
            if 'tracks' not in st.session_state:
                st.session_state.tracks = []

            def add_track():
                st.session_state.tracks.append({'title': '', 'composers': []})

            def remove_track(index):
                st.session_state.tracks.pop(index)

            cols_header = st.columns([6, 6, 1])
            cols_header[0].write("**Título da Faixa**")
            cols_header[1].write("**Compositor(es)**")
            
            all_composers_flat = sorted(list(set(item for sublist in df['composers'].dropna().apply(format_string_to_list) for item in sublist)))

            for i, track in enumerate(st.session_state.tracks):
                cols = st.columns([6, 6, 1])
                st.session_state.tracks[i]['title'] = cols[0].text_input(f"Título Faixa {i+1}", value=track['title'], label_visibility="collapsed")
                st.session_state.tracks[i]['composers'] = cols[1].multiselect(f"Compositores Faixa {i+1}", options=all_composers_flat, default=track['composers'], label_visibility="collapsed")
                cols[2].button("🗑️", key=f"del_{i}", on_click=remove_track, args=(i,))

            st.button("Adicionar mais uma faixa", on_click=add_track)

            submitted = st.form_submit_button("Salvar Álbum")
            if submitted:
                if not album_artists and not new_artist_input:
                    st.error("É necessário informar pelo menos um artista.")
                elif not album_title:
                    st.error("O título do álbum é obrigatório.")
                elif not st.session_state.tracks:
                    st.error("Adicione pelo menos uma faixa ao álbum.")
                else:
                    final_artists = album_artists
                    if new_artist_input and new_artist_input not in final_artists:
                        final_artists.append(new_artist_input)
                    
                    new_rows = []
                    for i, track in enumerate(st.session_state.tracks):
                        if track['title']: # Só adiciona se o título não estiver vazio
                            new_row = {
                                'trackNumber': i + 1,
                                'title': track['title'],
                                'artists': format_list_to_string(final_artists),
                                'album': album_title,
                                'year': album_year,
                                'composers': format_list_to_string(track['composers']),
                                'rating_jom': np.nan,
                                'rating_jov': np.nan,
                                'rating_job': np.nan
                            }
                            new_rows.append(new_row)
                    
                    if new_rows:
                        new_df = pd.DataFrame(new_rows)
                        df_updated = pd.concat([df, new_df], ignore_index=True)
                        conn.update(worksheet="Musicas", data=df_updated)
                        st.success(f"Álbum '{album_title}' adicionado com sucesso!")
                        st.session_state.tracks = [] # Limpa a lista de faixas
                    else:
                        st.warning("Nenhuma faixa com título foi adicionada.")

    if add_type == "Música Avulsa":
        with st.form("add_song_form", clear_on_submit=True):
            st.subheader("Informações da Música")
            
            # Lógica para artistas
            all_artists_flat = sorted(list(set(item for sublist in df['artists'].dropna().apply(format_string_to_list) for item in sublist)))
            song_artists = st.multiselect("Artista(s)", options=all_artists_flat)
            
            # Lógica para álbum
            if song_artists:
                # Mostra álbuns dos artistas selecionados
                artist_albums_df = df[df['artists'].apply(lambda x: any(artist in format_string_to_list(x) for artist in song_artists))]
                album_options = sorted(artist_albums_df['album'].dropna().unique())
            else:
                album_options = []

            album_choice = st.selectbox("Álbum", options=["Novo Álbum"] + album_options)
            
            if album_choice == "Novo Álbum":
                song_album = st.text_input("Nome do Novo Álbum")
                song_year = st.number_input("Ano", min_value=1900, max_value=2100, step=1)
            else:
                song_album = album_choice
                # Preenche o ano automaticamente
                year_val = int(df[df['album'] == song_album]['year'].iloc[0])
                song_year = st.number_input("Ano", value=year_val, disabled=True)

            song_title = st.text_input("Título da Música")
            track_number = st.number_input("Número da Faixa", min_value=1, step=1)

            # Lógica para compositores
            all_composers_flat = sorted(list(set(item for sublist in df['composers'].dropna().apply(format_string_to_list) for item in sublist)))
            song_composers = st.multiselect("Compositor(es)", options=all_composers_flat)

            submitted = st.form_submit_button("Salvar Música")
            if submitted:
                if not song_artists or not song_album or not song_title:
                    st.error("Artista, Álbum e Título são campos obrigatórios.")
                else:
                    new_row = pd.DataFrame([{
                        'trackNumber': track_number,
                        'title': song_title,
                        'artists': format_list_to_string(song_artists),
                        'album': song_album,
                        'year': song_year,
                        'composers': format_list_to_string(song_composers),
                        'rating_jom': np.nan,
                        'rating_jov': np.nan,
                        'rating_job': np.nan
                    }])
                    df_updated = pd.concat([df, new_row], ignore_index=True)
                    conn.update(worksheet="Musicas", data=df_updated)
                    st.success(f"Música '{song_title}' adicionada com sucesso!")

# --- LÓGICA PARA AS ABAS "PRÓXIMOS A OUVIR" E "CONCLUÍDOS" ---
if not df.empty:
    # Agrupando por álbum para calcular estatísticas
    album_stats = df.groupby(['album', 'artists', 'year']).agg(
        total_tracks=('title', 'count'),
        rated_tracks=(USER_RATING_COL, lambda x: x.notna().sum()),
        avg_rating=(USER_RATING_COL, 'mean')
    ).reset_index()
    album_stats['completion_perc'] = (album_stats['rated_tracks'] / album_stats['total_tracks']) * 100

    # DataFrame para próximos a ouvir (incompletos)
    next_to_listen = album_stats[album_stats['completion_perc'] < 100].sort_values(
        by='completion_perc', ascending=False
    )
    
    # DataFrame para concluídos
    completed_albums = album_stats[album_stats['completion_perc'] == 100].sort_values(
        by='avg_rating', ascending=False
    )
else:
    next_to_listen = pd.DataFrame()
    completed_albums = pd.DataFrame()

with tab3:
    st.header(f"Sua jornada musical, {st.session_state.user.upper()}")
    st.markdown("Álbuns para você explorar, ordenados pelo seu progresso.")
    
    # Filtros para "Próximos a Ouvir"
    f_col1, f_col2 = st.columns(2)
    all_artists_flat = sorted(list(set(item for sublist in next_to_listen['artists'].dropna().apply(format_string_to_list) for item in sublist)))
    
    artist_filter_next = f_col1.multiselect("Filtrar por Artista", options=all_artists_flat, key="artist_next")
    year_options_next = sorted(next_to_listen['year'].dropna().unique().astype(int))
    year_filter_next = f_col2.multiselect("Filtrar por Ano", options=year_options_next, key="year_next")

    filtered_next = next_to_listen.copy()
    if artist_filter_next:
        filtered_next = filtered_next[filtered_next['artists'].apply(lambda x: any(artist in format_string_to_list(x) for artist in artist_filter_next))]
    if year_filter_next:
        filtered_next = filtered_next[filtered_next['year'].isin(year_filter_next)]

    if filtered_next.empty:
        st.info("Nenhum álbum para mostrar com os filtros atuais, ou você já ouviu tudo!")
    else:
        for index, row in filtered_next.iterrows():
            with st.container(border=True):
                c1, c2, c3, c4 = st.columns([4, 2, 2, 1])
                c1.subheader(f"{row['album']}")
                c1.caption(f"{row['artists']} ({int(row['year'])})")
                
                c2.metric("Progresso", f"{row['completion_perc']:.1f}%")
                c3.metric("Faixas Avaliadas", f"{row['rated_tracks']}/{row['total_tracks']}")

                if c4.button("✏️", key=f"edit_next_{index}", help="Editar este álbum"):
                    st.session_state.editing_album = (row['album'], row['artists'])
                    st.rerun()


with tab4:
    st.header("🏆 Álbuns 100% Avaliados por Você")
    st.markdown("Sua galeria de álbuns finalizados, classificados pela sua nota média.")
    
    # Filtros para "Concluídos"
    fc_col1, fc_col2 = st.columns(2)
    all_artists_completed = sorted(list(set(item for sublist in completed_albums['artists'].dropna().apply(format_string_to_list) for item in sublist)))
    
    artist_filter_completed = fc_col1.multiselect("Filtrar por Artista", options=all_artists_completed, key="artist_completed")
    year_options_completed = sorted(completed_albums['year'].dropna().unique().astype(int))
    year_filter_completed = fc_col2.multiselect("Filtrar por Ano", options=year_options_completed, key="year_completed")

    filtered_completed = completed_albums.copy()
    if artist_filter_completed:
        filtered_completed = filtered_completed[filtered_completed['artists'].apply(lambda x: any(artist in format_string_to_list(x) for artist in artist_filter_completed))]
    if year_filter_completed:
        filtered_completed = filtered_completed[filtered_completed['year'].isin(year_filter_completed)]

    if filtered_completed.empty:
        st.info("Você ainda não completou a avaliação de nenhum álbum.")
    else:
        for index, row in filtered_completed.iterrows():
            color = get_color_for_rating(row['avg_rating'])
            label = get_rating_label(row['avg_rating'])
            
            st.markdown(f"""
            <div style="border: 2px solid {color}; border-radius: 10px; padding: 15px; margin-bottom: 10px;">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <h3 style="margin: 0; color: {color};">{row['album']}</h3>
                        <p style="margin: 0; color: #888;">{row['artists']} ({int(row['year'])})</p>
                    </div>
                    <div style="text-align: right;">
                        <p style="margin: 0; font-size: 1.5em; font-weight: bold; color: {color};">{row['avg_rating']:.2f}</p>
                        <p style="margin: 0; color: {color};">{label}</p>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # Adicionando o botão de edição fora do HTML para funcionalidade
            if st.button("✏️ Editar", key=f"edit_comp_{index}", help="Editar este álbum"):
                st.session_state.editing_album = (row['album'], row['artists'])
                st.rerun()