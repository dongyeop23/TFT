import os
import duckdb
import flet as ft

# ==============================================================================
# 1. 데이터베이스 초기화 및 다중 CSV 통합 파싱 함수
# ==============================================================================
def init_database():
    conn = duckdb.connect("tft_meta.db")
    cursor = conn.cursor()

    cursor.execute("DROP TABLE IF EXISTS ChampionTrait;")
    cursor.execute("DROP TABLE IF EXISTS Deck;")
    cursor.execute("DROP TABLE IF EXISTS Champion;")
    cursor.execute("DROP TABLE IF EXISTS Item;")
    cursor.execute("DROP TABLE IF EXISTS Trait;")

    cursor.execute("""
        CREATE TABLE Champion (
            champion_id INTEGER PRIMARY KEY,
            name VARCHAR(50),
            cost INTEGER,
            hp INTEGER,
            attack_damage INTEGER,
            image_path VARCHAR(255)
        );
    """)

    cursor.execute("""
        CREATE TABLE Item (
            item_id INTEGER PRIMARY KEY,
            item_name VARCHAR(50),
            effect TEXT,
            image_path VARCHAR(255)
        );
    """)

    cursor.execute("""
        CREATE TABLE Trait (
            trait_id INTEGER PRIMARY KEY,
            trait_name VARCHAR(50),
            description TEXT
        );
    """)

    cursor.execute("""
        CREATE TABLE ChampionTrait (
            champion_id INTEGER,
            trait_id INTEGER,
            PRIMARY KEY (champion_id, trait_id)
        );
    """)

    cursor.execute("""
        CREATE TABLE Deck (
            deck_id INTEGER PRIMARY KEY,
            deck_name VARCHAR(100),
            description TEXT,
            rank_tier VARCHAR(10),
            user_id INTEGER
        );
    """)

    csv_path = os.path.join("data", "assets.csv")
    if not os.path.exists(csv_path):
        print(f"에러: {csv_path} 파일이 존재하지 않습니다.")
        return conn

    with open(csv_path, "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f.readlines()]

    current_section = None

    for line in lines:
        if not line:
            continue

        if line.startswith("champion_id,name,cost,hp,attack_damage,image_path"):
            current_section = "champion"
            continue
        elif line.startswith("item_id,item_name,effect,image_path"):
            current_section = "item"
            continue
        elif line.startswith("trait_id,trait_name,description"):
            current_section = "trait"
            continue
        elif line.startswith("champion_id,trait_id"):
            current_section = "champion_trait"
            continue
        elif line.startswith("deck_id,deck_name,description,rank_tier,user_id"):
            current_section = "deck"
            continue

        parts = line.split(",")

        try:
            if current_section == "champion":
                cursor.execute(
                    "INSERT INTO Champion VALUES (?, ?, ?, ?, ?, ?)",
                    (int(parts[0]), parts[1], int(parts[2]), int(parts[3]), int(parts[4]), parts[5])
                )
            elif current_section == "item":
                cursor.execute(
                    "INSERT INTO Item VALUES (?, ?, ?, ?)",
                    (int(parts[0]), parts[1], parts[2], parts[3])
                )
            elif current_section == "trait":
                description = ",".join(parts[2:])
                cursor.execute(
                    "INSERT INTO Trait VALUES (?, ?, ?)",
                    (int(parts[0]), parts[1], description)
                )
            elif current_section == "champion_trait":
                cursor.execute(
                    "INSERT INTO ChampionTrait VALUES (?, ?)",
                    (int(parts[0]), int(parts[1]))
                )
            elif current_section == "deck":
                description = ",".join(parts[2:-2])
                rank_tier = parts[-2]
                user_id = int(parts[-1])
                cursor.execute(
                    "INSERT INTO Deck VALUES (?, ?, ?, ?, ?)",
                    (int(parts[0]), parts[1], description, rank_tier, user_id)
                )
        except Exception as e:
            print(f"파싱 오류 (섹션: {current_section}, 라인: {line}): {e}")

    conn.commit()
    print("assets.csv 데이터 성공적으로 데이터베이스에 로드 완료!")
    return conn


# ==============================================================================
# 2. Repository 패턴 구현
# ==============================================================================
class ChampionRepository:
    def __init__(self, conn):
        self.conn = conn

    def find_all(self):
        return self.conn.execute("SELECT * FROM Champion ORDER BY cost DESC").fetchall()


class DeckRepository:
    def __init__(self, conn):
        self.conn = conn

    def find_all_decks(self):
        return self.conn.execute("SELECT * FROM Deck ORDER BY rank_tier ASC").fetchall()


# ==============================================================================
# 3. Flet 기반 GUI UI 애플리케이션
# ==============================================================================
def main(page: ft.Page):
    page.title = "TFT META BUILDER"
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 30
    page.scroll = ft.ScrollMode.AUTO

    conn = init_database()
    champ_repo = ChampionRepository(conn)
    deck_repo = DeckRepository(conn)

    # --- 상단 타이틀 ---
    header = ft.Column([
        ft.Text("TFT META BUILDER", size=32, weight=ft.FontWeight.BOLD, color=ft.Colors.AMBER),
        ft.Text("데이터베이스 텀 프로젝트 - 대시보드", size=16, color=ft.Colors.GREY_400),
        ft.Divider(color=ft.Colors.AMBER_400)
    ])

    # --- 메타 덱 목록 ---
    deck_cards = []
    for deck in deck_repo.find_all_decks():
        deck_cards.append(
            ft.Card(
                content=ft.Container(
                    content=ft.Column([
                        ft.ListTile(
                            leading=ft.Icon(ft.Icons.LOCAL_FIRE_DEPARTMENT, color=ft.Colors.ORANGE),
                            title=ft.Text(f"{deck[1]} (티어: {deck[3]})", weight=ft.FontWeight.BOLD),
                            subtitle=ft.Text(deck[2]),
                        ),
                        ft.Row(
                            [ft.Text(f"작성자 ID: {deck[4]}", size=12, color=ft.Colors.GREY_400)],
                            alignment=ft.MainAxisAlignment.END,
                        )
                    ]),
                    padding=10
                ),
                width=400
            )
        )

    deck_section = ft.Column([
        ft.Text("추천 메타 덱 목록", size=24, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_200),
        ft.Row(deck_cards, wrap=True)
    ])

    # --- 챔피언 목록 ---
    champ_grid = ft.GridView(
        expand=False,
        runs_count=5,
        max_extent=220,
        child_aspect_ratio=1.0,
        spacing=15,
        run_spacing=15,
        height=600,
    )

    for champ in champ_repo.find_all():
        champ_grid.controls.append(
            ft.Container(
                content=ft.Column([
                    ft.Icon(ft.Icons.PERSON, size=40, color=ft.Colors.AMBER_200),
                    ft.Text(champ[1], weight=ft.FontWeight.BOLD, size=16),
                    ft.Text(f"가격: {champ[2]}골드", color=ft.Colors.YELLOW_600),
                    ft.Text(f"체력: {champ[3]} / 공격력: {champ[4]}", size=12, color=ft.Colors.GREY_300)
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                bgcolor=ft.Colors.with_opacity(0.3, ft.Colors.BLUE_GREY),
                border_radius=10,
                padding=10,
            )
        )

    champ_section = ft.Column([
        ft.Text("챔피언 도감", size=24, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_200),
        champ_grid
    ], spacing=10)

    page.add(
        header,
        ft.Container(height=20),
        deck_section,
        ft.Container(height=30),
        champ_section
    )


if __name__ == "__main__":
    ft.app(main)