import streamlit as st
import osmnx as ox
import networkx as nx
import folium
from folium.plugins import AntPath
import math
from pathlib import Path
import pickle

# ====== CẤU HÌNH TRANG & CSS ======
st.set_page_config(
    page_title="Greedy Traffic Navigator - TP.HCM", 
    layout="wide",
)

# Custom CSS để làm đẹp giao diện
st.markdown("""
<style>
    /* Giảm padding và margin */
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 1rem;
    }
    
    /* Header đẹp */
    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 12px;
        color: white;
        margin-bottom: 1.5rem;
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
    }
    
    /* Card styling gọn gàng */
    .custom-card {
        background: white;
        padding: 1.2rem;
        border-radius: 10px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        border-left: 4px solid #667eea;
        margin-bottom: 1rem;
    }
    
    /* Metric cards nhỏ gọn */
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 0.8rem;
        border-radius: 8px;
        color: white;
        text-align: center;
    }
    
    /* Scrollable container gọn */
    .scrollable-container {
        max-height: 250px;
        overflow-y: auto;
        border: 1px solid #e0e0e0;
        border-radius: 8px;
        padding: 0.8rem;
        background: #f8f9fa;
        margin-bottom: 1rem;
    }
    
    /* Path step items nhỏ gọn */
    .path-step {
        background: white;
        padding: 0.6rem;
        margin: 0.3rem 0;
        border-radius: 6px;
        border-left: 3px solid #667eea;
        box-shadow: 0 1px 2px rgba(0,0,0,0.05);
        font-size: 0.9rem;
    }
    
    /* Button styling */
    .stButton button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        padding: 0.5rem 1.5rem;
        border-radius: 20px;
        font-weight: 600;
        transition: all 0.3s ease;
        width: 100%;
    }
    
    /* Sidebar compact */
    .sidebar .sidebar-content {
        padding: 1rem;
    }
    
    /* Giảm khoảng cách giữa các elements */
    .element-container {
        margin-bottom: 0.8rem;
    }
    
    /* Radio button compact */
    .stRadio > div {
        background: #f8f9fa;
        padding: 0.8rem;
        border-radius: 8px;
        border: 1px solid #e0e0e0;
        margin-bottom: 0.5rem;
    }
    
    /* CSS cho scrollable container lớn hơn */
    .large-scroll-container {
        max-height: 350px;
        overflow-y: auto;
        border: 1px solid #e0e0e0;
        border-radius: 8px;
        padding: 0.8rem;
        background: #f8f9fa;
        margin-bottom: 1rem;
    }
    .compact-path-step {
        background: white;
        padding: 0.6rem;
        margin: 0.3rem 0;
        border-radius: 6px;
        border-left: 3px solid #667eea;
        box-shadow: 0 1px 2px rgba(0,0,0,0.05);
        font-size: 0.85rem;
        line-height: 1.4;
    }
</style>
""", unsafe_allow_html=True)

# ====== HEADER ĐẸP ======
st.markdown("""
<div class="main-header">
    <h1 style="margin:0; font-size: 2rem;">Greedy Traffic Navigator - TP.HCM</h1>
    <p style="margin:0; font-size: 1rem; opacity: 0.9;">Thuật toán tham lam tối ưu lộ trình giao thông - TP.HCM</p>
</div>
""", unsafe_allow_html=True)

# ====== KHỞI TẠO SESSION STATE ======
if 'results_calculated' not in st.session_state:
    st.session_state.results_calculated = False
if 'all_paths' not in st.session_state:
    st.session_state.all_paths = []
if 'selected_path_index' not in st.session_state:
    st.session_state.selected_path_index = 0
if 'greedy_path' not in st.session_state:
    st.session_state.greedy_path = []
if 'visited_edges' not in st.session_state:
    st.session_state.visited_edges = []

# ====== SIDEBAR COMPACT ======
with st.sidebar:
    st.markdown("### 🎯 Thiết lập")
    
    # Danh sách quận
    districts = {
        "Quận 1": "District 1, Ho Chi Minh City, Vietnam",
        "Quận 3": "District 3, Ho Chi Minh City, Vietnam",
        "Quận 4": "District 4, Ho Chi Minh City, Vietnam",
        "Quận 5": "District 5, Ho Chi Minh City, Vietnam",
        "Quận 6": "District 6, Ho Chi Minh City, Vietnam",
        "Quận 7": "District 7, Ho Chi Minh City, Vietnam",
        "Quận 10": "District 10, Ho Chi Minh City, Vietnam",
        "Quận 11": "District 11, Ho Chi Minh City, Vietnam",
        "Bình Thạnh": "Binh Thanh District, Ho Chi Minh City, Vietnam",
        "Gò Vấp": "Go Vap District, Ho Chi Minh City, Vietnam",
        "Tân Bình": "Tan Binh District, Ho Chi Minh City, Vietnam",
        "Phú Nhuận": "Phu Nhuan District, Ho Chi Minh City, Vietnam",
        "Thủ Đức": "Thu Duc City, Ho Chi Minh City, Vietnam"
    }
    
    selected_district = st.selectbox("🏙️ Khu vực", list(districts.keys()))
    
    # Cache và tải đồ thị
    CACHE_DIR = Path("cache_graphs")
    CACHE_DIR.mkdir(exist_ok=True)

    def get_graph_from_cache(place_name):
        cache_file = CACHE_DIR / f"{place_name.replace(',', '').replace(' ', '_')}.pkl"
        if cache_file.exists():
            with open(cache_file, "rb") as f:
                return pickle.load(f)
        try:
            gdf = ox.geocode_to_gdf(place_name)
            if not gdf.empty and gdf.geometry.iloc[0].geom_type in ["Polygon", "MultiPolygon"]:
                G = ox.graph_from_polygon(gdf.geometry.iloc[0], network_type="drive", simplify=True)
            else:
                raise ValueError
        except Exception:
            lat, lon = ox.geocode(place_name)
            dist = 3000
            north, south, east, west = ox.utils_geo.bbox_from_point((lat, lon), dist=dist)
            G = ox.graph_from_bbox(north, south, east, west, network_type="drive", simplify=True)
        with open(cache_file, "wb") as f:
            pickle.dump(G, f)
        return G

    def multigraph_to_digraph(G_multi):
        G = nx.DiGraph()
        for u, v, data in G_multi.edges(data=True):
            length = data.get('length', 1)
            if G.has_edge(u, v):
                if length < G[u][v]['length']:
                    G[u][v]['length'] = length
            else:
                G.add_edge(u, v, length=length)
        for n, data in G_multi.nodes(data=True):
            G.add_node(n, **data)
        return G

    # Tải bản đồ
    with st.spinner(f"🔄 Đang tải {selected_district}..."):
        G_multi = get_graph_from_cache(districts[selected_district])
        G_simple = multigraph_to_digraph(G_multi)

    # Node mapping
    node_mapping = {node: f"N{i+1:03d}" for i, node in enumerate(G_multi.nodes())}
    reverse_mapping = {v: k for k, v in node_mapping.items()}
    nodes_short = list(node_mapping.values())

    # Chọn điểm
    st.markdown("---")
    st.subheader("📍 Chọn điểm")
    
    start_short = st.selectbox("Điểm bắt đầu", nodes_short, key="start")
    end_short = st.selectbox("Điểm kết thúc", nodes_short, index=min(10, len(nodes_short)-1), key="end")
    
    start_node = reverse_mapping[start_short]
    end_node = reverse_mapping[end_short]

    # Hiển thị thông tin node ngắn gọn
    start_lat, start_lon = G_multi.nodes[start_node]['y'], G_multi.nodes[start_node]['x']
    end_lat, end_lon = G_multi.nodes[end_node]['y'], G_multi.nodes[end_node]['x']
    
    st.markdown(f"""
    <div style="background: #f0f2f6; padding: 0.8rem; border-radius: 8px; margin: 0.5rem 0; font-size: 0.9rem;">
        <div style="display: flex; justify-content: space-between;">
            <div>
                <strong>🚦 Start:</strong><br>
                <small>{node_mapping[start_node]}</small>
            </div>
            <div>
                <strong>🏁 End:</strong><br>
                <small>{node_mapping[end_node]}</small>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    # ====== KIỂM TRA ĐỔI QUẬN ĐỂ RESET SESSION ======
    if "prev_district" not in st.session_state:
        st.session_state.prev_district = selected_district

    # Nếu người dùng đổi quận, reset toàn bộ dữ liệu tạm
    if selected_district != st.session_state.prev_district:
        st.session_state.results_calculated = False
        st.session_state.all_paths = []
        st.session_state.greedy_path = []
        st.session_state.visited_edges = []
        st.session_state.selected_path_index = 0
        st.session_state.prev_district = selected_district
        st.rerun()

# ====== CÁC HÀM THUẬT TOÁN ======
def heuristic(n1, n2):
    x1, y1 = G_multi.nodes[n1]['x'], G_multi.nodes[n1]['y']
    x2, y2 = G_multi.nodes[n2]['x'], G_multi.nodes[n2]['y']
    return math.sqrt((x1 - x2)**2 + (y1 - y2)**2)

def greedy_best_first(G, start, goal):
    from heapq import heappush, heappop
    open_set = []
    heappush(open_set, (heuristic(start, goal), start))
    came_from = {}
    visited_edges = []
    visited = set()
    while open_set:
        _, current = heappop(open_set)
        if current == goal:
            break
        if current in visited:
            continue
        visited.add(current)
        for neighbor in G.neighbors(current):
            if neighbor not in visited:
                came_from[neighbor] = current
                heappush(open_set, (heuristic(neighbor, goal), neighbor))
                visited_edges.append((current, neighbor))
    path = [goal]
    while path[-1] != start:
        if path[-1] not in came_from:
            return [], visited_edges
        path.append(came_from[path[-1]])
    path.reverse()
    return path, visited_edges

def find_truly_different_paths(G, start, end, max_paths=3, similarity_threshold=0.3):
    def path_similarity(path1, path2):
        set1 = set(path1)
        set2 = set(path2)
        if not set1 or not set2:
            return 0
        intersection = len(set1.intersection(set2))
        union = len(set1.union(set2))
        return intersection / union
    
    all_paths = []
    
    try:
        shortest_path = nx.shortest_path(G, start, end, weight='length')
        all_paths.append(shortest_path)
    except: pass
    
    try:
        alt_path1 = nx.shortest_path(G, start, end, weight=None)
        if (alt_path1 not in all_paths and 
            not any(path_similarity(alt_path1, p) > similarity_threshold for p in all_paths)):
            all_paths.append(alt_path1)
    except: pass
    
    if len(all_paths) > 0 and len(all_paths[0]) > 3:
        try:
            mid_index = len(all_paths[0]) // 2
            if mid_index < len(all_paths[0]):
                avoid_node = all_paths[0][mid_index]
                G_temp = G.copy()
                if G_temp.has_node(avoid_node):
                    G_temp.remove_node(avoid_node)
                    alt_path2 = nx.shortest_path(G_temp, start, end, weight='length')
                    if (alt_path2 not in all_paths and 
                        not any(path_similarity(alt_path2, p) > similarity_threshold for p in all_paths)):
                        all_paths.append(alt_path2)
        except: pass
    
    all_paths.sort(key=lambda path: sum(G[u][v]['length'] for u, v in zip(path[:-1], path[1:])))
    return all_paths[:max_paths]

# ====== HIỂN THỊ BẢN ĐỒ KHU VỰC (LUÔN HIỂN THỊ) ======
center_lat = sum(nx.get_node_attributes(G_multi, 'y').values()) / len(G_multi.nodes)
center_lon = sum(nx.get_node_attributes(G_multi, 'x').values()) / len(G_multi.nodes)
m = folium.Map(location=[center_lat, center_lon], zoom_start=13)
for node in G_multi.nodes():
    folium.CircleMarker([G_multi.nodes[node]['y'], G_multi.nodes[node]['x']],
                        radius=2, color="gray", fill=True, fill_opacity=0.6,
                        tooltip=f"{node_mapping[node]}").add_to(m)

# Chỉ hiển thị bản đồ khu vực khi CHƯA có kết quả
if not st.session_state.results_calculated:
    st.markdown("### 🗺️ Bản đồ khu vực")
    st.components.v1.html(m._repr_html_(), height=500)

# ====== NÚT CHẠY THUẬT TOÁN ======
if st.button("**BẮT ĐẦU TÌM ĐƯỜNG**", use_container_width=True):
    with st.spinner("🔄 Đang tính toán các đường đi..."):
        path, visited_edges = greedy_best_first(G_multi, start_node, end_node)
        if path:
            all_paths = find_truly_different_paths(G_simple, start_node, end_node, max_paths=3)
            
            if (path not in all_paths and 
                not any(len(set(path).intersection(set(p))) / len(set(path).union(set(p))) > 0.7 for p in all_paths)):
                all_paths.append(path)
            
            all_paths = all_paths[:3]
            
            st.session_state.results_calculated = True
            st.session_state.all_paths = all_paths
            st.session_state.greedy_path = path
            st.session_state.visited_edges = visited_edges
            st.session_state.selected_path_index = 0
            
            st.success(f"✅ Đã tìm thấy {len(all_paths)} đường đi!")
        else:
            st.error("❌ Không tìm thấy đường đi!")

# ====== HIỂN THỊ KẾT QUẢ ======
if st.session_state.results_calculated and st.session_state.all_paths:
    all_paths = st.session_state.all_paths
    greedy_path = st.session_state.greedy_path
    visited_edges = st.session_state.visited_edges
    
    # BỐ CỤC: 2 CỘT TRÊN
    col_top1, col_top2 = st.columns([2, 1])
    
    with col_top1:
        st.markdown('<div class="custom-card"><h3>🗺️ Bản đồ tổng quan</h3></div>', unsafe_allow_html=True)
        
        # Tạo bản đồ tổng quan
        m_map = folium.Map(location=[center_lat, center_lon], zoom_start=14)
        
        # Marker
        folium.Marker([G_multi.nodes[start_node]['y'], G_multi.nodes[start_node]['x']],
                      tooltip=f"🚦 Start: {node_mapping[start_node]}",
                      icon=folium.Icon(color="green")).add_to(m_map)
        folium.Marker([G_multi.nodes[end_node]['y'], G_multi.nodes[end_node]['x']],
                      tooltip=f"🏁 End: {node_mapping[end_node]}",
                      icon=folium.Icon(color="red")).add_to(m_map)
        
        # Các cạnh đã duyệt
        for u, v in visited_edges:
            folium.PolyLine([(G_multi.nodes[u]['y'], G_multi.nodes[u]['x']),
                             (G_multi.nodes[v]['y'], G_multi.nodes[v]['x'])],
                            color="orange", weight=2, opacity=0.4).add_to(m_map)
        
        # Đường đi tham lam
        AntPath([(G_multi.nodes[n]['y'], G_multi.nodes[n]['x']) for n in greedy_path],
                color="blue", weight=6, delay=800, tooltip="Đường đi tham lam").add_to(m_map)
        
        # Các đường đi khác
        colors = ['red', 'purple', 'darkgreen']
        for i, path_item in enumerate(all_paths):
            if i < len(colors):
                color = colors[i]
                total_dist = sum(G_simple[u][v]['length'] for u, v in zip(path_item[:-1], path_item[1:])) / 1000
                AntPath([(G_multi.nodes[n]['y'], G_multi.nodes[n]['x']) for n in path_item],
                        color=color, weight=4, delay=800, 
                        tooltip=f"Đường {i+1}: {total_dist:.2f} km").add_to(m_map)
        
        st.components.v1.html(m_map._repr_html_(), height=400)
    
    with col_top2:
        st.markdown('<div class="custom-card"><h3>📊 Lựa chọn đường đi</h3></div>', unsafe_allow_html=True)
        
        # Chọn đường đi
        path_options = []
        for i, path_item in enumerate(all_paths):
            total_dist = sum(G_simple[u][v]['length'] for u, v in zip(path_item[:-1], path_item[1:])) / 1000
            path_type = " 🎯" if path_item == greedy_path else ""
            path_options.append(f"Đường {i+1}{path_type} - {total_dist:.2f}km")
        
        selected_index = st.radio(
            "Chọn đường đi:",
            range(len(all_paths)),
            index=st.session_state.selected_path_index,
            format_func=lambda x: path_options[x],
            key="path_selector"
        )
        
        if selected_index != st.session_state.selected_path_index:
            st.session_state.selected_path_index = selected_index
            st.rerun()
        
        selected_path = all_paths[selected_index]
        
        # Thông tin đường đi
        total_distance = sum(G_simple[u][v]['length'] for u, v in zip(selected_path[:-1], selected_path[1:])) / 1000
        
        col_metric1, col_metric2 = st.columns(2)
        with col_metric1:
            st.markdown(f"""
            <div class="metric-card">
                <div style="font-size: 0.8rem;">📏 Quãng đường</div>
                <div style="font-size: 1.2rem; font-weight: bold;">{total_distance:.2f} km</div>
            </div>
            """, unsafe_allow_html=True)
        with col_metric2:
            st.markdown(f"""
            <div class="metric-card">
                <div style="font-size: 0.8rem;">🔢 Số node</div>
                <div style="font-size: 1.2rem; font-weight: bold;">{len(selected_path)}</div>
            </div>
            """, unsafe_allow_html=True)
    
    # ====== BẢN ĐỒ CHI TIẾT BÊN DƯỚI ======
    st.markdown("---")
    col_bottom1, col_bottom2 = st.columns([2, 1])
    
    with col_bottom1:
        st.markdown('<div class="custom-card"><h3>🔍 Bản đồ chi tiết - Đường được chọn</h3></div>', unsafe_allow_html=True)
        
        # Bản đồ chi tiết cho đường được chọn
        m_detail = folium.Map(location=[center_lat, center_lon], zoom_start=15)
        
        # Marker với thông tin chi tiết
        folium.Marker([G_multi.nodes[start_node]['y'], G_multi.nodes[start_node]['x']],
                      tooltip=f"🚦 BẮT ĐẦU: {node_mapping[start_node]}",
                      popup=f"<b>ĐIỂM BẮT ĐẦU</b><br>Node: {node_mapping[start_node]}<br>Tọa độ: ({start_lat:.4f}, {start_lon:.4f})",
                      icon=folium.Icon(color="green", icon="play")).add_to(m_detail)
        
        folium.Marker([G_multi.nodes[end_node]['y'], G_multi.nodes[end_node]['x']],
                      tooltip=f"🏁 KẾT THÚC: {node_mapping[end_node]}",
                      popup=f"<b>ĐIỂM KẾT THÚC</b><br>Node: {node_mapping[end_node]}<br>Tọa độ: ({end_lat:.4f}, {end_lon:.4f})",
                      icon=folium.Icon(color="red", icon="flag")).add_to(m_detail)
        
        # Đường đi được chọn với màu nổi bật
        colors_detail = ['#ff4444', '#aa66cc', '#228B22']
        color_detail = colors_detail[selected_index] if selected_index < len(colors_detail) else '#3366cc'
        
        AntPath([(G_multi.nodes[n]['y'], G_multi.nodes[n]['x']) for n in selected_path],
                color=color_detail, weight=8, delay=600,
                tooltip=f"Đường {selected_index+1} - {total_distance:.2f} km").add_to(m_detail)
        
        # Thêm các node quan trọng trên đường đi
        if len(selected_path) > 4:
            for i, node in enumerate(selected_path):
                if i % max(1, len(selected_path)//8) == 0:
                    folium.CircleMarker(
                        [G_multi.nodes[node]['y'], G_multi.nodes[node]['x']],
                        radius=4,
                        color=color_detail,
                        fill=True,
                        fill_opacity=0.8,
                        tooltip=f"Node: {node_mapping[node]}"
                    ).add_to(m_detail)
        
        st.components.v1.html(m_detail._repr_html_(), height=400)
    
    with col_bottom2:
        st.markdown('<div class="custom-card"><h3>📋 Chi tiết lộ trình</h3></div>', unsafe_allow_html=True)
        
        # Chi tiết các bước với container lớn hơn
        total_steps = len(selected_path) - 1
        
        # Tạo nội dung scrollable ĐƠN GIẢN và ĐÚNG CÚ PHÁP
        scroll_items = []
        max_display_steps = 100
        total_steps = len(selected_path) - 1

        for i, (u, v) in enumerate(zip(selected_path[:-1], selected_path[1:])):
            if i >= max_display_steps:
                break
            dist = G_simple[u][v]['length']
            scroll_items.append(
                f"<div class='compact-path-step'>"
                f"<strong>Bước {i+1}/{total_steps}:</strong> {node_mapping[u]} → {node_mapping[v]}<br>"
                f"<small style='color: #666;'>📏 {dist:.0f} m</small>"
                f"</div>"
            )

        # Thêm thông báo nếu vượt quá max
        if total_steps > max_display_steps:
            scroll_items.append(
                f"<div class='compact-path-step' style='background:#fff3cd; border-left:3px solid #ffc107;'>"
                f"<strong>📋 Đang hiển thị {max_display_steps}/{total_steps} bước</strong><br>"
                f"<small>Đường đi có tổng cộng {total_steps} bước</small>"
                f"</div>"
            )

        # Ghép tất cả thành một HTML duy nhất
        scroll_html = "<div class='large-scroll-container'>" + "".join(scroll_items) + "</div>"
        st.markdown(scroll_html, unsafe_allow_html=True)
        
        # Thông tin tổng quan
        avg_step_length = (total_distance * 1000) / total_steps if total_steps > 0 else 0
        st.markdown(f"""
        <div style="background: #e7f9ff; padding: 0.8rem; border-radius: 8px; margin: 0.5rem 0; font-size: 0.9rem;">
            <strong>📊 Tổng quan đường đi:</strong><br>
            • <strong>{total_steps} bước</strong> • <strong>{total_distance:.2f} km</strong><br>
            • Trung bình: <strong>{avg_step_length:.1f} m/bước</strong>
        </div>
        """, unsafe_allow_html=True)

# ====== NÚT RESET ======
if st.session_state.results_calculated:
    st.markdown("---")
    if st.button("🔄 **TÍNH LẠI TỪ ĐẦU**", use_container_width=True):
        st.session_state.results_calculated = False
        st.session_state.all_paths = []
        st.session_state.selected_path_index = 0
        st.session_state.greedy_path = []
        st.session_state.visited_edges = []
        st.rerun()