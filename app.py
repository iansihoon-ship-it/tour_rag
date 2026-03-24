import streamlit as st
import pandas as pd
import numpy as np
import folium
from folium.plugins import MarkerCluster, HeatMap
from streamlit_folium import st_folium
import math
import plotly.express as px
import random
from i18n import TRANSLATIONS

# 지역 / 지하철역 좌표 사전
SEOUL_LOCATIONS = {
    "서울시청": (37.5665, 126.9780),
    "강남역": (37.4979, 127.0276),
    "홍대입구역": (37.5568, 126.9242),
    "서울역": (37.5546, 126.9706),
    "명동": (37.5636, 126.9800),
    "이태원": (37.5340, 126.9940),
    "여의도": (37.5219, 126.9243),
    "종로3가역": (37.5704, 126.9921),
    "잠실역": (37.5133, 127.1001),
    "성수역": (37.5446, 127.0560),
    "건대입구역": (37.5404, 127.0692),
    "신촌역": (37.5552, 126.9368),
    "합정역": (37.5495, 126.9139)
}

# 페이지 설정
st.set_page_config(
    page_title="관광지 추천 & cs챗봇 서비스",
    page_icon="🗺️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# =====================================================================
# 1. 데이터 파이프라인 (Data Mockup & Pre-processing)
# =====================================================================

@st.cache_data
def generate_mock_data():
    """
    실제 CSV 파일이 없을 경우를 대비하여 더미 데이터를 생성하는 함수.
    """
    np.random.seed(42)
    
    # 1. 세대별 인기관광지 (Demographic Data)
    places = ["코엑스", "롯데월드잠실점", "국립중앙박물관", "여의도한강공원", "남산서울타워", "경복궁", "서울숲", "북촌한옥마을"]
    ages = ["20대", "30대", "40대", "50대이상", "전체"]
    
    popular_df = pd.DataFrame({
        "관광지ID": [f"POI_{i}" for i in range(len(places) * len(ages))],
        "관심지점명": np.random.choice(places, len(places) * len(ages)),
        "구분": np.random.choice(["관광명소", "문화생활시설", "레저/스포츠", "공원"], len(places) * len(ages)),
        "연령대": np.repeat(ages, len(places)),
        "비율": np.random.uniform(1.0, 15.0, len(places) * len(ages)).round(1),
        "성장율": np.random.uniform(10.0, 150.0, len(places) * len(ages)).round(1)
    })
    
    # 2. 메인 관광지 로케이션 데이터 (지도 매핑용)
    num_locations = 200
    lats = np.random.uniform(37.45, 37.60, num_locations)
    lons = np.random.uniform(126.85, 127.15, num_locations)
    
    real_places_pool = [
        "N서울타워", "동대문디자인플라자(DDP)", "인사동", "명동거리", "국립현대미술관",
        "별마당 도서관", "예술의전당", "덕수궁", "창덕궁", "청계천",
        "올림픽공원", "보라매공원", "광장시장", "경의선숲길", "이태원 앤틱가구거리",
        "경리단길", "망원시장", "홍대 걷고싶은거리", "서대문형무소역사관", "선유도공원",
        "하늘공원", "노들섬", "세빛섬", "가로수길", "압구정 로데오거리",
        "청담동 명품거리", "양재천", "서울어린이대공원", "건대 맛의거리", "서울함공원",
        "낙산공원", "동묘시장", "광화문광장", "익선동 한옥거리", "서촌 한옥마을",
        "연트럴파크", "석촌호수", "방이동 먹자골목", "송리단길", "올림픽공원 평화의문",
        "혜화문", "창경궁", "종묘", "대학로 마로니에공원", "남대문시장",
        "이화벽화마을", "성수동 카페거리", "뚝섬유원지", "서울바이오허브", "서울식물원"
    ]
    
    base_locations = pd.DataFrame({
        "관심지점명": np.random.choice(real_places_pool, num_locations, replace=True),
        "구분": np.random.choice(["관광명소", "맛집/카페", "쇼핑", "공원"], num_locations),
        "테마": np.random.choice(["일반", "K-Movie", "핫플레이스"], num_locations, p=[0.5, 0.2, 0.3]),
        "LC_LA": lats, # 위도
        "LC_LO": lons, # 경도
        "AVRG_SCORE_VALUE": np.random.uniform(3.5, 5.0, num_locations).round(1),
        "REVIEW_CO": np.random.randint(10, 5000, num_locations),
        "연령대": np.random.choice(["20대", "30대", "40대", "50대이상", "전체"], num_locations)
    })
    
    real_spots = [("코엑스", 37.511, 127.059), ("남산", 37.553, 126.981), ("이태원", 37.538, 126.992), ("경복궁", 37.579, 126.977)]
    for idx, (name, lat, lon) in enumerate(real_spots):
        base_locations.loc[idx, "관심지점명"] = name
        base_locations.loc[idx, "LC_LA"] = lat
        base_locations.loc[idx, "LC_LO"] = lon
        base_locations.loc[idx, "테마"] = "K-Movie" if idx % 2 == 0 else "핫플레이스"
        
    base_locations["LC_LA"].fillna(37.5665, inplace=True)
    base_locations["LC_LO"].fillna(126.9780, inplace=True)
    
    descriptions = []
    for _, row in base_locations.iterrows():
        if row["테마"] == "K-Movie":
            movies = ["오징어 게임", "이태원 클라쓰", "사랑의 불시착", "기생충", "빈센조", "도깨비", "눈물의 여왕"]
            descriptions.append(f"'{np.random.choice(movies)}' 촬영지")
        elif row["테마"] == "핫플레이스":
            reasons = ["SNS 인증샷 핫플", "2030 방문자 1위", "최근 1개월 검색량 폭발", "주말 웨이팅 성지"]
            descriptions.append(np.random.choice(reasons))
        else:
            descriptions.append("현지인이 즐겨찾는 명소")
    base_locations["설명"] = descriptions
    
    return popular_df, base_locations

# =====================================================================
# 2. 복합 스코어링 알고리즘 (Backend Logic)
# =====================================================================

def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)
    dlon = lon2_rad - lon1_rad
    dlat = lat2_rad - lat1_rad
    a = math.sin(dlat / 2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

def calculate_recommendation_score(row, target_age, max_distance):
    dist = row["거리(km)"]
    if dist > max_distance: return 0
    dist_score = max(0, (max_distance - dist) / max_distance) * 40
    age_score = 20 if row["연령대"] == target_age or row["연령대"] == "전체" else 5
    rating_score = (row["AVRG_SCORE_VALUE"] / 5.0) * 20
    review_score = min((np.log1p(row["REVIEW_CO"]) / np.log1p(5000)) * 20, 20)
    return round(dist_score + age_score + rating_score + review_score, 1)

# =====================================================================
# 3. UI/UX 구성 (Streamlit - DashboardUI)
# =====================================================================

def render_sidebar(t, lang):
    st.sidebar.subheader(t["sidebar_lang"])
    lang_choice = st.sidebar.selectbox(
        "",
        options=["한국어", "English", "中文"],
        index=["ko", "en", "zh"].index(lang),
        label_visibility="collapsed"
    )
    lang_map = {"한국어": "ko", "English": "en", "中文": "zh"}
    if lang_map[lang_choice] != st.session_state["lang"]:
        st.session_state["lang"] = lang_map[lang_choice]
        st.rerun()
        
    st.sidebar.title(t["sidebar_title"])
    
    st.sidebar.subheader(t["sidebar_loc"])
    loc_keys = list(SEOUL_LOCATIONS.keys())
    loc_idx = st.sidebar.selectbox(
        t["loc_ph"],
        range(len(loc_keys)),
        format_func=lambda x: t.get("loc_options", loc_keys)[x]
    )
    location_keyword = loc_keys[loc_idx]
    current_lat, current_lon = SEOUL_LOCATIONS[location_keyword]
    st.sidebar.caption(f"{t.get('loc_caption', '선택된 좌표')}: {current_lat:.4f}, {current_lon:.4f}")
    
    st.sidebar.subheader(t["sidebar_cond"])
    radius_km = st.sidebar.slider(t["radius"], min_value=1.0, max_value=20.0, value=5.0, step=0.5)
    
    age_vals = ["전체", "20대", "30대", "40대", "50대이상"]
    age_idx = st.sidebar.selectbox(
        t["age_group"], 
        range(len(age_vals)),
        format_func=lambda x: t.get("age_options_disp", age_vals)[x]
    )
    age_group = age_vals[age_idx]
    
    theme_vals = ["K-Movie", "핫플레이스", "일반"]
    theme_idxs = st.sidebar.multiselect(
        t["theme_filter"], 
        range(len(theme_vals)),
        default=[0, 1],
        format_func=lambda x: t.get("theme_options_disp", theme_vals)[x]
    )
    theme = [theme_vals[i] for i in theme_idxs]
    
    return current_lat, current_lon, radius_km, age_group, theme

def render_kpi_cards(df, t):
    if df.empty:
        st.warning(t["no_data"])
        return
        
    col1, col2, col3, col4 = st.columns(4)
    avg_score = round(df["AVRG_SCORE_VALUE"].mean(), 1)
    max_review_idx = df["REVIEW_CO"].idxmax()
    top_place = df.loc[max_review_idx, "관심지점명"]
    total_spots = len(df)
    
    with col1:
        st.metric(label=t["kpi_total"], value=f"{total_spots}{t['kpi_total_unit']}")
    with col2:
        st.metric(label=t["kpi_avg"], value=f"{avg_score} / 5.0")
    with col3:
        st.metric(label=t["kpi_best"], value=top_place)
    with col4:
        st.metric(label=t["kpi_max"], value=f"{df['추천점수'].max():.1f}{t['kpi_max_unit']}")
        
    st.markdown("<br>", unsafe_allow_html=True)
    
    theme_scores = df.groupby("테마")["추천점수"].mean().reset_index()
    # Replace theme texts for chart
    if "theme_options_disp" in t:
        theme_map = dict(zip(["K-Movie", "핫플레이스", "일반"], t["theme_options_disp"]))
        theme_scores["테마_disp"] = theme_scores["테마"].map(theme_map)
    else:
        theme_scores["테마_disp"] = theme_scores["테마"]
        
    fig = px.bar(
        theme_scores, 
        x="테마_disp", 
        y="추천점수", 
        color="테마_disp",
        title=t["chart_title"],
        text_auto=".1f",
        template="plotly_white",
        height=300
    )
    fig.update_layout(showlegend=False, margin=dict(l=20, r=20, t=40, b=20), xaxis_title='', yaxis_title='')
    st.plotly_chart(fig, use_container_width=True)
        
def render_map(df, current_lat, current_lon, t):
    m = folium.Map(location=[current_lat, current_lon], zoom_start=12)
    folium.Marker(
        [current_lat, current_lon],
        popup=t["map_curr"],
        tooltip=t["map_user"],
        icon=folium.Icon(color="red", icon="info-sign")
    ).add_to(m)
    
    if df.empty:
        st_folium(m, width="100%", height=500)
        return

    marker_cluster = MarkerCluster().add_to(m)
    heat_data = []
    
    for idx, row in df.iterrows():
        lat, lon = row["LC_LA"], row["LC_LO"]
        # Map theme name inside popup
        theme_disp = row["테마"]
        if "theme_options_disp" in t:
             theme_map = dict(zip(["K-Movie", "핫플레이스", "일반"], t["theme_options_disp"]))
             theme_disp = theme_map.get(row["테마"], row["테마"])
             
        popup_html = f"<b>{row['관심지점명']}</b><br>{t['map_score']}: {row['AVRG_SCORE_VALUE']}<br>{t['map_review']}: {row['REVIEW_CO']}<br>{t['map_dist']}: {row['거리(km)']}km"
        
        folium.Marker(
            location=[lat, lon],
            popup=folium.Popup(popup_html, max_width=300),
            tooltip=f"{row['관심지점명']} ({row['추천점수']})",
            icon=folium.Icon(color="blue", icon="cloud" if row["테마"] == "K-Movie" else "star")
        ).add_to(marker_cluster)
        
        heat_data.append([lat, lon, row["추천점수"]])
        
    HeatMap(heat_data, radius=15).add_to(m)
    st_folium(m, width="100%", height=500)

def render_list(df, t):
    st.subheader(t["list_title"])
    if df.empty:
        st.info(t["list_no_data"])
        return
        
    display_df = df.sort_values(by="추천점수", ascending=False).head(10).reset_index(drop=True)
    display_df.index = display_df.index + 1
    
    styled_df = display_df[["관심지점명", "테마", "설명", "거리(km)", "AVRG_SCORE_VALUE", "REVIEW_CO", "추천점수"]]
    
    # Translate dataframe cells if necessary
    if "theme_options_disp" in t:
        theme_map = dict(zip(["K-Movie", "핫플레이스", "일반"], t["theme_options_disp"]))
        styled_df["테마"] = styled_df["테마"].map(theme_map)
        
    styled_df = styled_df.rename(columns={
        "관심지점명": t["col_name"],
        "테마": t["col_theme"],
        "설명": t.get("col_desc", "설명"),
        "거리(km)": t["col_dist"],
        "AVRG_SCORE_VALUE": t["col_score"],
        "REVIEW_CO": t["col_review"],
        "추천점수": t["col_rec"]
    })
    st.dataframe(styled_df, use_container_width=True)

# =====================================================================
# 4. RAG 챗봇 인터페이스 (Chatbot Integration)
# =====================================================================

def render_chatbot(df, t):
    st.subheader(t["chat_title"])
    st.caption(t["chat_desc"])
    
    if "messages" not in st.session_state:
        st.session_state["messages"] = [{"role": "assistant", "content": t["chat_hi"]}]
        
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            
    user_input = st.chat_input(t["chat_ph"])
    
    if user_input:
        st.session_state.messages.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.markdown(user_input)
            
        with st.chat_message("assistant"):
            if df.empty:
                response = t["chat_err"]
            else:
                user_msg = user_input.replace(" ", "")
                # Simple condition matching based on keywords (language agnostic simplified)
                is_movie = any(k in user_msg.lower() for k in ["촬영지", "영화", "드라마", "movie", "drama", "filming", "电影", "拍摄"])
                is_other = any(k in user_msg.lower() for k in ["다른", "말고", "other", "another", "else", "其他", "另外"])
                
                if is_movie:
                    movie_df = df[df["테마"] == "K-Movie"]
                    if not movie_df.empty:
                        target_place = movie_df.iloc[0]
                        prefix = t["chat_res_movie"]
                    else:
                        target_place = df.iloc[0]
                        prefix = t["chat_res_movie_alt"]
                elif is_other:
                    if len(df) > 1:
                        idx = random.randint(1, min(4, len(df)-1))
                        target_place = df.iloc[idx]
                        prefix = t["chat_res_other"]
                    else:
                        target_place = df.iloc[0]
                        prefix = t["chat_res_other_alt"]
                else:
                    target_place = df.iloc[0]
                    prefix = t["chat_res_def"]

                # Formatting the recommendation text
                theme_disp = target_place['테마']
                if "theme_options_disp" in t:
                    theme_map = dict(zip(["K-Movie", "핫플레이스", "일반"], t["theme_options_disp"]))
                    theme_disp = theme_map.get(theme_disp, theme_disp)
                    
                response = (f"{prefix}"
                            f"{t['chat_rec1']}{target_place['관심지점명']}{t['chat_rec2']}"
                            f"{t['chat_li_theme']}{theme_disp}\n"
                            f"{t['chat_li_score']}{target_place['AVRG_SCORE_VALUE']}{t['chat_li_rev']}{target_place['REVIEW_CO']}\n"
                            f"{t['chat_li_dist']}{target_place['거리(km)']}km\n"
                            f"{t['chat_footer']}")
            
            st.markdown(response)
            st.session_state.messages.append({"role": "assistant", "content": response})

# =====================================================================
# 5. Main Application Logic
# =====================================================================

def main():
    if "lang" not in st.session_state:
        st.session_state["lang"] = "ko"
        
    t = TRANSLATIONS[st.session_state["lang"]]
    
    st.title(t["title"])
    
    pop_df, loc_df = generate_mock_data()
    
    current_lat, current_lon, radius_km, age_group, theme = render_sidebar(t, st.session_state["lang"])
    
    filtered_df = loc_df.copy()
    if theme:
        filtered_df = filtered_df[filtered_df["테마"].isin(theme)]
        
    filtered_df["거리(km)"] = filtered_df.apply(
        lambda row: round(haversine(current_lat, current_lon, row["LC_LA"], row["LC_LO"]), 2), 
        axis=1
    )
    
    filtered_df["추천점수"] = filtered_df.apply(
        lambda row: calculate_recommendation_score(row, target_age=age_group, max_distance=radius_km), 
        axis=1
    )
    
    final_df = filtered_df[filtered_df["추천점수"] > 0].sort_values(by="추천점수", ascending=False).reset_index(drop=True)
    
    st.markdown("---")
    render_list(final_df, t)
    
    st.markdown("---")
    render_map(final_df, current_lat, current_lon, t)
    
    st.markdown("---")
    render_kpi_cards(final_df, t)
    
    st.markdown("---")
    render_chatbot(final_df, t)

if __name__ == "__main__":
    main()
