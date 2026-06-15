CREATE TABLE Users (
    user_id INTEGER PRIMARY KEY,
    nickname VARCHAR,
    email VARCHAR UNIQUE
);

CREATE TABLE Deck (
    deck_id INTEGER PRIMARY KEY,
    user_id INTEGER,
    deck_name VARCHAR,
    description TEXT,
    rank_tier VARCHAR,
    FOREIGN KEY (user_id) REFERENCES Users(user_id)
);

CREATE TABLE Champion (
    champion_id INTEGER PRIMARY KEY,
    name VARCHAR,
    cost INTEGER,
    hp INTEGER,
    attack_damage INTEGER,
    image_path VARCHAR
);

CREATE TABLE Trait (
    trait_id INTEGER PRIMARY KEY,
    trait_name VARCHAR UNIQUE,
    description TEXT
);

CREATE TABLE ChampionTrait (
    champion_id INTEGER,
    trait_id INTEGER,
    PRIMARY KEY (champion_id, trait_id),
    FOREIGN KEY (champion_id) REFERENCES Champion(champion_id),
    FOREIGN KEY (trait_id) REFERENCES Trait(trait_id)
);

CREATE TABLE Item (
    item_id INTEGER PRIMARY KEY,
    item_name VARCHAR,
    effect TEXT,
    image_path VARCHAR
);

CREATE TABLE ChampionItem (
    champion_id INTEGER,
    item_id INTEGER,
    PRIMARY KEY (champion_id, item_id),
    FOREIGN KEY (champion_id) REFERENCES Champion(champion_id),
    FOREIGN KEY (item_id) REFERENCES Item(item_id)
);

CREATE TABLE DeckChampion (
    deck_id INTEGER,
    champion_id INTEGER,
    PRIMARY KEY (deck_id, champion_id),
    FOREIGN KEY (deck_id) REFERENCES Deck(deck_id),
    FOREIGN KEY (champion_id) REFERENCES Champion(champion_id)
);