import streamlit as st
import pandas as pd
import numpy as np
import folium
from folium.plugins import MarkerCluster, HeatMap
from streamlit_folium import st_folium
from datetime import datetime
import math

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
    page_title="서울 맞춤형 관광지 추천 대시보드",
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
    세대별 인기관광지, 핫플레이스, 급등동네, SNS 영화 촬영지 등 4가지 성격의 데이터를 포함합니다.
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
    # 서울 강남/종로/여의도 등 중심 위경도로 랜덤 생성
    num_locations = 50
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
        "관심지점명": np.random.choice(real_places_pool, num_locations, replace=False),
        "구분": np.random.choice(["관광명소", "맛집/카페", "쇼핑", "공원"], num_locations),
        "테마": np.random.choice(["일반", "K-Movie", "핫플레이스"], num_locations, p=[0.5, 0.2, 0.3]),
        "LC_LA": lats, # 위도
        "LC_LO": lons, # 경도
        "AVRG_SCORE_VALUE": np.random.uniform(3.5, 5.0, num_locations).round(1),
        "REVIEW_CO": np.random.randint(10, 5000, num_locations),
        "연령대": np.random.choice(["20대", "30대", "40대", "50대이상", "전체"], num_locations)
    })
    
    # 실제 데이터 명칭을 몇 개 삽입
    real_spots = [("코엑스", 37.511, 127.059), ("남산", 37.553, 126.981), ("이태원", 37.538, 126.992), ("경복궁", 37.579, 126.977)]
    for idx, (name, lat, lon) in enumerate(real_spots):
        base_locations.loc[idx, "관심지점명"] = name
        base_locations.loc[idx, "LC_LA"] = lat
        base_locations.loc[idx, "LC_LO"] = lon
        base_locations.loc[idx, "테마"] = "K-Movie" if idx % 2 == 0 else "핫플레이스"
        
    # 결측치 처리 (모의)
    base_locations["LC_LA"].fillna(37.5665, inplace=True) # 서울시청 기본
    base_locations["LC_LO"].fillna(126.9780, inplace=True)
    
    return popular_df, base_locations

# =====================================================================
# 2. 복합 스코어링 알고리즘 (Backend Logic)
# =====================================================================

def haversine(lat1, lon1, lat2, lon2):
    """
    두 위경도 사이의 거리를 계산하는 Haversine 공식 (단위: km)
    """
    R = 6371.0 # 지구의 반지름 (km)
    
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)
    
    dlon = lon2_rad - lon1_rad
    dlat = lat2_rad - lat1_rad
    
    a = math.sin(dlat / 2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    distance = R * c
    return distance

def calculate_recommendation_score(row, target_age, max_distance):
    """
    거리, 평점, 리뷰 개수, 연령대 가중치를 기반으로 최종 추천 점수를 계산합니다.
    (거리 반비례 점수) + (연령대 매칭 점수) + (평점 가중치) + (리뷰수 가중치)
    """
    dist = row["거리(km)"]
    
    if dist > max_distance:
        return 0 # 반경을 벗어나면 0점 추천 제외
    
    # 거리가 0이면 최대 점수, 멀어질수록 감소
    dist_score = max(0, (max_distance - dist) / max_distance) * 40
    
    # 2. 연령별 인기도 가중치
    age_score = 20 if row["연령대"] == target_age or row["연령대"] == "전체" else 5
    
    # 3. 평점 가중치 (5점 만점 기준)
    rating_score = (row["AVRG_SCORE_VALUE"] / 5.0) * 20
    
    # 4. 리뷰수 가중치 (최대 5000개 기준 로그 스케일링으로 모방)
    review_score = min((np.log1p(row["REVIEW_CO"]) / np.log1p(5000)) * 20, 20)
    
    total_score = dist_score + age_score + rating_score + review_score
    return round(total_score, 1)

# =====================================================================
# 3. UI/UX 구성 (Streamlit - DashboardUI)
# =====================================================================

def render_sidebar():
    """사이드바: 사용자 입력 필터 렌더링"""
    st.sidebar.title("📍 추천 설정 필터")
    
    # 키워드 기반 위치 입력
    st.sidebar.subheader("1. 나의 현재 위치")
    location_keyword = st.sidebar.selectbox(
        "지역명 또는 지하철역 선택",
        options=list(SEOUL_LOCATIONS.keys())
    )
    current_lat, current_lon = SEOUL_LOCATIONS[location_keyword]
    st.sidebar.caption(f"선택된 좌표: {current_lat:.4f}, {current_lon:.4f}")
    
    st.sidebar.subheader("2. 탐색 조건")
    radius_km = st.sidebar.slider("검색 반경 (km)", min_value=1.0, max_value=20.0, value=5.0, step=0.5)
    
    age_group = st.sidebar.selectbox("타겟 연령대", ["전체", "20대", "30대", "40대", "50대이상"])
    
    theme = st.sidebar.multiselect(
        "테마 필터 (비워두면 전체)", 
        ["K-Movie", "핫플레이스", "일반"],
        default=["K-Movie", "핫플레이스"]
    )
    
    return current_lat, current_lon, radius_km, age_group, theme

import plotly.express as px

def render_kpi_cards(df):
    """상단 주요 KPI 지표 및 Plotly 차트 렌더링"""
    if df.empty:
        st.warning("선택된 조건에 맞는 관광지가 없습니다. 좌측 필터를 조정해주세요.")
        return
        
    col1, col2, col3, col4 = st.columns(4)
    
    avg_score = round(df["AVRG_SCORE_VALUE"].mean(), 1)
    max_review_idx = df["REVIEW_CO"].idxmax()
    top_place = df.loc[max_review_idx, "관심지점명"]
    total_spots = len(df)
    
    with col1:
        st.metric(label="검색된 관광지 수", value=f"{total_spots} 개")
    with col2:
        st.metric(label="평균 평점", value=f"{avg_score} / 5.0")
    with col3:
        st.metric(label="최다 리뷰 핫플레이스", value=top_place)
    with col4:
        st.metric(label="가장 높은 추천 점수", value=f"{df['추천점수'].max():.1f} 점")
        
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Plotly 시각화: 테마별 추천 점수 평균
    theme_scores = df.groupby("테마")["추천점수"].mean().reset_index()
    fig = px.bar(
        theme_scores, 
        x="테마", 
        y="추천점수", 
        color="테마",
        title="조회된 관광지의 테마별 평균 추천 점수",
        text_auto=".1f",
        template="plotly_white",
        height=300
    )
    fig.update_layout(showlegend=False, margin=dict(l=20, r=20, t=40, b=20))
    st.plotly_chart(fig, use_container_width=True)
        
def render_map(df, current_lat, current_lon):
    """Folium을 이용한 클러스터 매핑 및 히트맵 렌더링"""
    # 맵 초기화
    m = folium.Map(location=[current_lat, current_lon], zoom_start=12)
    
    # 사용자 현재 위치 (빨간색 마커)
    folium.Marker(
        [current_lat, current_lon],
        popup="현재 위치",
        tooltip="사용자 현 위치",
        icon=folium.Icon(color="red", icon="info-sign")
    ).add_to(m)
    
    if df.empty:
        st_folium(m, width="100%", height=500)
        return

    # 마커 클러스터
    marker_cluster = MarkerCluster().add_to(m)
    
    heat_data = []
    
    for idx, row in df.iterrows():
        lat, lon = row["LC_LA"], row["LC_LO"]
        popup_html = f"<b>{row['관심지점명']}</b><br>평점: {row['AVRG_SCORE_VALUE']}<br>리뷰: {row['REVIEW_CO']}<br>거리: {row['거리(km)']}km"
        
        folium.Marker(
            location=[lat, lon],
            popup=folium.Popup(popup_html, max_width=300),
            tooltip=f"{row['관심지점명']} ({row['추천점수']}점)",
            icon=folium.Icon(color="blue", icon="cloud" if row["테마"] == "K-Movie" else "star")
        ).add_to(marker_cluster)
        
        # 히트맵 데이터 (위치 및 추천점수 기준)
        heat_data.append([lat, lon, row["추천점수"]])
        
    # 히트맵 추가
    HeatMap(heat_data, radius=15).add_to(m)
    
    st_folium(m, width="100%", height=500)

def render_list(df):
    """추천 리스트 데이터프레임 렌더링"""
    st.subheader("📋 위치 기반 맞춤형 Top 10 추천 관광지")
    
    if df.empty:
        st.info("조건에 맞는 관광지가 없어 리스트를 표시할 수 없습니다.")
        return
        
    display_df = df.sort_values(by="추천점수", ascending=False).head(10).reset_index(drop=True)
    display_df.index = display_df.index + 1
    
    styled_df = display_df[["관심지점명", "테마", "연령대", "거리(km)", "AVRG_SCORE_VALUE", "REVIEW_CO", "추천점수"]].rename(columns={
        "AVRG_SCORE_VALUE": "평점",
        "REVIEW_CO": "리뷰수"
    })
    
    st.dataframe(styled_df, use_container_width=True)

# =====================================================================
# 4. RAG 챗봇 인터페이스 (Chatbot Integration)
# =====================================================================

def render_chatbot(df):
    """
    모의(Mock) RAG 챗봇 UI. 
    사용자 입력을 받아 필터링된 현재 df 상태를 기반으로 추천 텍스트를 응답합니다.
    """
    st.subheader("💬 맞춤형 관광지 추천 AI 어시스턴트 (RAG 모의)")
    st.caption("현재 필터링된 데이터를 바탕으로 질문에 답변합니다.")
    
    if "messages" not in st.session_state:
        st.session_state["messages"] = [{"role": "assistant", "content": "안녕하세요! 추천을 원하시는 관광 테마나 특정 조건이 있으면 말씀해주세요."}]
        
    # 기존 메시지 렌더링
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            
    # 새 입력
    user_input = st.chat_input("예: 20대가 좋아할 만한 핫플 추천해줘")
    
    if user_input:
        # 사용자 메시지 저장
        st.session_state.messages.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.markdown(user_input)
            
        # RAG 모의 응답 로직
        with st.chat_message("assistant"):
            if df.empty:
                response = "죄송합니다, 현재 설정된 범위와 조건에 맞는 데이터가 없습니다."
            else:
                user_msg = user_input.replace(" ", "")
                import random
                
                # 매우 간단한 의도(Intent) 파악용 Mock 로직
                if "촬영지" in user_msg or "영화" in user_msg or "드라마" in user_msg:
                    movie_df = df[df["테마"] == "K-Movie"]
                    if not movie_df.empty:
                        target_place = movie_df.iloc[0]
                        prefix = "영화/드라마 촬영지 테마로 분석한 결과입니다. 🎥\n\n"
                    else:
                        target_place = df.iloc[0]
                        prefix = "반경 내 촬영지 데이터가 부족하여, 대신 가장 인기 있는 핫플레이스를 추천해 드릴게요!\n\n"
                elif "다른" in user_msg or "말고" in user_msg:
                    if len(df) > 1:
                        idx = random.randint(1, min(4, len(df)-1))
                        target_place = df.iloc[idx]
                        prefix = "네, 알겠습니다! 새로운 곳으로 다시 찾아보았어요. 🔄\n\n"
                    else:
                        target_place = df.iloc[0]
                        prefix = "현재 반경 내에서는 이곳이 최선의 선택입니다 ㅠㅠ\n\n"
                else:
                    target_place = df.iloc[0]
                    prefix = "질문하신 내용에 기반하여 분석한 결과입니다. 📊\n\n"

                response = (f"{prefix}"
                            f"추천 점수 상위권인 **'{target_place['관심지점명']}'**을(를) 추천합니다.\n"
                            f"- 테마: {target_place['테마']}\n"
                            f"- 평점: ⭐ {target_place['AVRG_SCORE_VALUE']} / 리뷰: {target_place['REVIEW_CO']}개\n"
                            f"- 현재 위치에서의 거리: {target_place['거리(km)']}km\n"
                            f"\n이외에도 지도와 하단 리스트에서 다양한 대안을 확인하실 수 있습니다!")
            
            st.markdown(response)
            st.session_state.messages.append({"role": "assistant", "content": response})

# =====================================================================
# 5. Main Application Logic
# =====================================================================

def main():
    st.title("🌐 세대 및 위치 기반 서울 관광지 추천 대시보드")
    
    # 1. 데이터 로드 (모의 데이터)
    pop_df, loc_df = generate_mock_data()
    
    # 2. 사이드바 UI 렌더링 및 입력값 받기
    current_lat, current_lon, radius_km, age_group, theme = render_sidebar()
    
    # 3. 데이터 필터링 및 스코어링 로직
    # 테마 필터 (선택안했으면 조건 무시)
    filtered_df = loc_df.copy()
    if theme:
        filtered_df = filtered_df[filtered_df["테마"].isin(theme)]
        
    # 1. 거리 먼저 계산
    filtered_df["거리(km)"] = filtered_df.apply(
        lambda row: round(haversine(current_lat, current_lon, row["LC_LA"], row["LC_LO"]), 2), 
        axis=1
    )
    
    # 2. 점수 계산 및 거리 필터링
    filtered_df["추천점수"] = filtered_df.apply(
        lambda row: calculate_recommendation_score(row, target_age=age_group, max_distance=radius_km), 
        axis=1
    )
    
    # 점수가 0 이상인 곳(반경 내) 포함, 점수 높은 순 정렬
    final_df = filtered_df[filtered_df["추천점수"] > 0].sort_values(by="추천점수", ascending=False).reset_index(drop=True)
    
    # 4. 메인 화면 UI 레이아웃
    st.markdown("---")
    render_kpi_cards(final_df)
    
    st.markdown("---")
    render_map(final_df, current_lat, current_lon)
    
    st.markdown("---")
    render_list(final_df)
    
    st.markdown("---")
    render_chatbot(final_df)

if __name__ == "__main__":
    main()
