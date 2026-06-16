import os
import duckdb
import flet as ft

# ==============================================================================
# 1. 데이터베이스 초기화
# ==============================================================================
def init_database():
    conn = duckdb.connect("tft_meta.db")
    cursor = conn.cursor()

    cursor.execute("DROP TABLE IF EXISTS DeckChampion;")
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
            effect TEXT
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
            user_id VARCHAR(50)
        );
    """)
    cursor.execute("""
        CREATE TABLE DeckChampion (
            deck_id INTEGER,
            champion_id INTEGER,
            PRIMARY KEY (deck_id, champion_id)
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
        elif line.startswith("item_id,item_name,effect"):
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
                # image_path 없음 - item_id, item_name, effect(나머지 전부)
                effect = ",".join(parts[2:])
                cursor.execute(
                    "INSERT INTO Item VALUES (?, ?, ?)",
                    (int(parts[0]), parts[1], effect)
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
                user_id = parts[-1]
                cursor.execute(
                    "INSERT INTO Deck VALUES (?, ?, ?, ?, ?)",
                    (int(parts[0]), parts[1], description, rank_tier, user_id)
                )
        except Exception as e:
            print(f"파싱 오류 (섹션: {current_section}, 라인: {line}): {e}")

    # 덱별 챔피언 구성 하드코딩 삽입
    # 덱 1: 선봉대 벡스 카르마 덱 → 벡스(1), 블리츠크랭크(2), 소나(3), 카르마(4), 누누와 윌럼프(5), 일라오이(6), 모데카이저(7), 꼬마 정령(8)
    deck1_champs = [1, 2, 3, 4, 5, 6, 7, 8]
    for cid in deck1_champs:
        cursor.execute("INSERT INTO DeckChampion VALUES (?, ?)", (1, cid))

    # 덱 2: 별돌보미 자야 덱 → 자야(9), 진(10), 블리츠크랭크(2), 탐 켄치(11), 누누와 윌럼프(5), 라아스트(12), 잭스(13), 아트록스(14)
    deck2_champs = [9, 10, 2, 11, 5, 12, 13, 14]
    for cid in deck2_champs:
        cursor.execute("INSERT INTO DeckChampion VALUES (?, ?)", (2, cid))

    conn.commit()
    print("assets.csv 데이터 로드 완료!")
    return conn


# ==============================================================================
# 2. Repository
# ==============================================================================
class ChampionRepository:
    def __init__(self, conn):
        self.conn = conn

    def find_all(self):
        return self.conn.execute("SELECT * FROM Champion ORDER BY cost DESC").fetchall()

    def find_traits(self, champion_id):
        return self.conn.execute("""
            SELECT t.trait_name, t.description
            FROM Trait t
            JOIN ChampionTrait ct ON t.trait_id = ct.trait_id
            WHERE ct.champion_id = ?
        """, [champion_id]).fetchall()


class DeckRepository:
    def __init__(self, conn):
        self.conn = conn

    def find_all_decks(self):
        return self.conn.execute("SELECT * FROM Deck ORDER BY rank_tier ASC").fetchall()

    def find_champions_in_deck(self, deck_id):
        return self.conn.execute("""
            SELECT c.*
            FROM Champion c
            JOIN DeckChampion dc ON c.champion_id = dc.champion_id
            WHERE dc.deck_id = ?
            ORDER BY c.cost DESC
        """, [deck_id]).fetchall()


class ItemRepository:
    def __init__(self, conn):
        self.conn = conn

    def find_recommended(self, champion_id):
        champ = self.conn.execute(
            "SELECT cost FROM Champion WHERE champion_id = ?", [champion_id]
        ).fetchone()
        if not champ:
            return []
        cost = champ[0]
        if cost >= 4:
            items = self.conn.execute(
                "SELECT * FROM Item WHERE item_id IN (1, 3, 8, 9, 12) LIMIT 3"
            ).fetchall()
        elif cost == 3:
            items = self.conn.execute(
                "SELECT * FROM Item WHERE item_id IN (5, 6, 9, 11) LIMIT 3"
            ).fetchall()
        else:
            items = self.conn.execute(
                "SELECT * FROM Item WHERE item_id IN (2, 4, 6, 10) LIMIT 3"
            ).fetchall()
        return items


# ==============================================================================
# 3. Flet UI
# ==============================================================================
def main(page: ft.Page):
    page.title = "TFT META BUILDER"
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 30
    page.scroll = ft.ScrollMode.AUTO

    conn = init_database()
    champ_repo = ChampionRepository(conn)
    deck_repo = DeckRepository(conn)
    item_repo = ItemRepository(conn)

    all_champions = champ_repo.find_all()

    cost_colors = {
        1: ft.Colors.GREY_400,
        2: ft.Colors.GREEN_400,
        3: ft.Colors.BLUE_400,
        4: ft.Colors.PURPLE_400,
        5: ft.Colors.AMBER_400,
    }

    # ==========================================================================
    # 챔피언 상세 다이얼로그
    # ==========================================================================
    def show_champion_detail(champ):
        champion_id = champ[0]
        name = champ[1]
        cost = champ[2]
        hp = champ[3]
        ad = champ[4]
        image_path = champ[5].strip()
        border_color = cost_colors.get(cost, ft.Colors.GREY_400)

        traits = champ_repo.find_traits(champion_id)
        items = item_repo.find_recommended(champion_id)

        trait_rows = [
            ft.Container(
                content=ft.Column([
                    ft.Text(t[0], weight=ft.FontWeight.BOLD, color=ft.Colors.CYAN_300, size=13),
                    ft.Text(t[1], size=12, color=ft.Colors.GREY_300),
                ], spacing=2),
                bgcolor=ft.Colors.with_opacity(0.2, ft.Colors.CYAN),
                border_radius=6,
                padding=6,
            )
            for t in traits
        ]

        item_rows = [
            ft.Container(
                content=ft.Row([
                    ft.Icon(ft.Icons.STAR, size=24, color=ft.Colors.AMBER),
                    ft.Column([
                        ft.Text(i[1], weight=ft.FontWeight.BOLD, size=13),
                        ft.Text(i[2], size=11, color=ft.Colors.GREY_300),
                    ], spacing=2, expand=True),
                ], spacing=10),
                bgcolor=ft.Colors.with_opacity(0.2, ft.Colors.AMBER),
                border_radius=6,
                padding=6,
            )
            for i in items
        ]

        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Row([
                ft.Container(
                    content=ft.Image(
                        src=image_path,
                        width=60,
                        height=60,
                        fit="cover",
                        error_content=ft.Icon(ft.Icons.PERSON, size=40, color=ft.Colors.AMBER_200),
                    ),
                    border_radius=8,
                    clip_behavior=ft.ClipBehavior.HARD_EDGE,
                    border=ft.Border.all(2, border_color),
                ),
                ft.Column([
                    ft.Text(name, size=22, weight=ft.FontWeight.BOLD),
                    ft.Text(f"{cost}골드", color=border_color, size=14),
                ], spacing=2),
            ], spacing=15),
            content=ft.Container(
                width=420,
                content=ft.Column([
                    ft.Text("능력치", weight=ft.FontWeight.BOLD, color=ft.Colors.AMBER, size=15),
                    ft.Row([
                        ft.Container(
                            content=ft.Column([
                                ft.Icon(ft.Icons.FAVORITE, color=ft.Colors.RED_400, size=18),
                                ft.Text(str(hp), weight=ft.FontWeight.BOLD, size=16),
                                ft.Text("체력", size=11, color=ft.Colors.GREY_400),
                            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=2),
                            bgcolor=ft.Colors.with_opacity(0.15, ft.Colors.RED),
                            border_radius=8,
                            padding=12,
                            expand=True,
                        ),
                        ft.Container(
                            content=ft.Column([
                                ft.Icon(ft.Icons.FLASH_ON, color=ft.Colors.ORANGE_400, size=18),
                                ft.Text(str(ad), weight=ft.FontWeight.BOLD, size=16),
                                ft.Text("공격력", size=11, color=ft.Colors.GREY_400),
                            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=2),
                            bgcolor=ft.Colors.with_opacity(0.15, ft.Colors.ORANGE),
                            border_radius=8,
                            padding=12,
                            expand=True,
                        ),
                        ft.Container(
                            content=ft.Column([
                                ft.Icon(ft.Icons.DIAMOND, color=border_color, size=18),
                                ft.Text(f"{cost}골드", weight=ft.FontWeight.BOLD, size=16),
                                ft.Text("비용", size=11, color=ft.Colors.GREY_400),
                            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=2),
                            bgcolor=ft.Colors.with_opacity(0.15, border_color),
                            border_radius=8,
                            padding=12,
                            expand=True,
                        ),
                    ], spacing=10),
                    ft.Divider(color=ft.Colors.GREY_700),
                    ft.Text("시너지", weight=ft.FontWeight.BOLD, color=ft.Colors.AMBER, size=15),
                    *trait_rows,
                    ft.Divider(color=ft.Colors.GREY_700),
                    ft.Text("추천 아이템", weight=ft.FontWeight.BOLD, color=ft.Colors.AMBER, size=15),
                    *item_rows,
                ], spacing=10, scroll=ft.ScrollMode.AUTO),
            ),
            actions=[
                ft.TextButton("닫기", on_click=lambda e: close_dlg(dlg)),
            ],
        )
        page.overlay.append(dlg)
        dlg.open = True
        page.update()

    def close_dlg(dlg):
        dlg.open = False
        page.update()

    # ==========================================================================
    # 덱 상세 다이얼로그
    # ==========================================================================
    def show_deck_detail(deck):
        deck_id = deck[0]
        deck_name = deck[1]
        deck_desc = deck[2]
        deck_tier = deck[3]

        matched_champs = deck_repo.find_champions_in_deck(deck_id)

        champ_cards = []
        for champ in matched_champs:
            border_color = cost_colors.get(champ[2], ft.Colors.GREY_400)
            champ_cards.append(
                ft.Container(
                    content=ft.Column([
                        ft.Container(
                            content=ft.Image(
                                src=champ[5].strip(),
                                width=60,
                                height=60,
                                fit="cover",
                                error_content=ft.Icon(ft.Icons.PERSON, size=30, color=ft.Colors.AMBER_200),
                            ),
                            border_radius=6,
                            clip_behavior=ft.ClipBehavior.HARD_EDGE,
                        ),
                        ft.Text(champ[1], size=11, weight=ft.FontWeight.BOLD),
                        ft.Text(f"{champ[2]}골드", size=10, color=border_color),
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=3),
                    bgcolor=ft.Colors.with_opacity(0.3, ft.Colors.BLUE_GREY),
                    border=ft.Border.all(2, border_color),
                    border_radius=8,
                    padding=8,
                    width=90,
                )
            )

        tier_color = ft.Colors.AMBER if deck_tier == "1" else ft.Colors.BLUE_200

        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Column([
                ft.Row([
                    ft.Icon(ft.Icons.LOCAL_FIRE_DEPARTMENT, color=ft.Colors.ORANGE),
                    ft.Text(deck_name, size=18, weight=ft.FontWeight.BOLD),
                    ft.Container(
                        content=ft.Text(f"Tier {deck_tier}", size=12, weight=ft.FontWeight.BOLD, color=tier_color),
                        bgcolor=ft.Colors.with_opacity(0.2, tier_color),
                        border_radius=6,
                        padding=4,
                    ),
                ], spacing=10),
                ft.Text(deck_desc, size=13, color=ft.Colors.GREY_300),
            ], spacing=6),
            content=ft.Container(
                width=500,
                content=ft.Column([
                    ft.Text("덱 챔피언 구성", weight=ft.FontWeight.BOLD, color=ft.Colors.AMBER, size=15),
                    ft.Row(champ_cards, wrap=True, spacing=8, run_spacing=8),
                ], spacing=10, scroll=ft.ScrollMode.AUTO),
            ),
            actions=[
                ft.TextButton("닫기", on_click=lambda e: close_dlg(dlg)),
            ],
        )
        page.overlay.append(dlg)
        dlg.open = True
        page.update()

    # ==========================================================================
    # 헤더
    # ==========================================================================
    header = ft.Column([
        ft.Text("TFT META BUILDER", size=32, weight=ft.FontWeight.BOLD, color=ft.Colors.AMBER),
        ft.Text("데이터베이스 텀 프로젝트 - 대시보드", size=16, color=ft.Colors.GREY_400),
        ft.Divider(color=ft.Colors.AMBER_400),
    ])

    # ==========================================================================
    # 메타 덱 목록
    # ==========================================================================
    deck_cards = []
    for deck in deck_repo.find_all_decks():
        d = deck
        tier_color = ft.Colors.AMBER if d[3] == "1" else ft.Colors.BLUE_200
        deck_cards.append(
            ft.Card(
                content=ft.Container(
                    content=ft.Column([
                        ft.ListTile(
                            leading=ft.Icon(ft.Icons.LOCAL_FIRE_DEPARTMENT, color=ft.Colors.ORANGE),
                            title=ft.Text(f"{d[1]}", weight=ft.FontWeight.BOLD),
                            subtitle=ft.Text(d[2], size=12),
                        ),
                        ft.Row([
                            ft.Container(
                                content=ft.Text(f"Tier {d[3]}", size=12, weight=ft.FontWeight.BOLD, color=tier_color),
                                bgcolor=ft.Colors.with_opacity(0.2, tier_color),
                                border_radius=6,
                                padding=4,
                            ),
                            ft.TextButton(
                                "덱 자세히 보기",
                                icon=ft.Icons.ARROW_FORWARD,
                                on_click=lambda e, deck=d: show_deck_detail(deck),
                            ),
                        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    ]),
                    padding=10,
                ),
                width=430,
            )
        )

    deck_section = ft.Column([
        ft.Text("추천 메타 덱 목록", size=24, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_200),
        ft.Row(deck_cards, wrap=True, spacing=15),
    ])

    # ==========================================================================
    # 챔피언 목록
    # ==========================================================================
    champ_grid = ft.GridView(
        expand=False,
        runs_count=7,
        max_extent=160,
        child_aspect_ratio=0.8,
        spacing=12,
        run_spacing=12,
        height=700,
    )

    for champ in all_champions:
        border_color = cost_colors.get(champ[2], ft.Colors.GREY_400)
        c = champ
        champ_grid.controls.append(
            ft.GestureDetector(
                on_tap=lambda e, champ=c: show_champion_detail(champ),
                content=ft.Container(
                    content=ft.Column([
                        ft.Container(
                            content=ft.Image(
                                src=champ[5].strip(),
                                width=80,
                                height=80,
                                fit="cover",
                                error_content=ft.Icon(ft.Icons.PERSON, size=40, color=ft.Colors.AMBER_200),
                            ),
                            border_radius=8,
                            clip_behavior=ft.ClipBehavior.HARD_EDGE,
                        ),
                        ft.Text(champ[1], weight=ft.FontWeight.BOLD, size=13),
                        ft.Text(f"{champ[2]}골드", color=border_color, size=11),
                        ft.Text(f"HP {champ[3]}  AD {champ[4]}", size=10, color=ft.Colors.GREY_300),
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=4),
                    bgcolor=ft.Colors.with_opacity(0.3, ft.Colors.BLUE_GREY),
                    border=ft.Border.all(2, border_color),
                    border_radius=10,
                    padding=10,
                    ink=True,
                ),
            )
        )

    champ_section = ft.Column([
        ft.Text("챔피언 도감  (클릭하면 상세 정보)", size=24, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_200),
        champ_grid,
    ], spacing=10)

    page.add(
        header,
        ft.Container(height=20),
        deck_section,
        ft.Container(height=30),
        champ_section,
    )


if __name__ == "__main__":
    ft.app(main)