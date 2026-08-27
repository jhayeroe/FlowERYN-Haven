from pathlib import Path
import json

root = Path('.')
db_path = root / 'app/src/main/java/com/floweryn/costing/DBHelper.java'
gradle_path = root / 'app/build.gradle'
seed_path = root / 'app/src/main/assets/seed_data.json'

db = db_path.read_text(encoding='utf-8')

old_create = 'CREATE TABLE products (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL UNIQUE COLLATE NOCASE, effort REAL NOT NULL DEFAULT 0, other_cost REAL NOT NULL DEFAULT 0)'
new_create = 'CREATE TABLE products (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL COLLATE NOCASE, effort REAL NOT NULL DEFAULT 0, other_cost REAL NOT NULL DEFAULT 0)'
if old_create not in db and new_create not in db:
    raise SystemExit('Expected products schema was not found')
db = db.replace(old_create, new_create)

db = db.replace('private static final int DB_VERSION = 1;', 'private static final int DB_VERSION = 2;')

old_upgrade = '@Override public void onUpgrade(SQLiteDatabase db, int oldVersion, int newVersion) { }'
new_upgrade = '''@Override public void onUpgrade(SQLiteDatabase db, int oldVersion, int newVersion) {
        if (oldVersion < 2) {
            db.execSQL("ALTER TABLE product_materials RENAME TO product_materials_old");
            db.execSQL("ALTER TABLE products RENAME TO products_old");
            db.execSQL("CREATE TABLE products (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL COLLATE NOCASE, effort REAL NOT NULL DEFAULT 0, other_cost REAL NOT NULL DEFAULT 0)");
            db.execSQL("CREATE TABLE product_materials (id INTEGER PRIMARY KEY AUTOINCREMENT, product_id INTEGER NOT NULL, material_id INTEGER NOT NULL, qty REAL NOT NULL, FOREIGN KEY(product_id) REFERENCES products(id) ON DELETE CASCADE, FOREIGN KEY(material_id) REFERENCES materials(id) ON DELETE RESTRICT)");
            db.execSQL("INSERT INTO products (id,name,effort,other_cost) SELECT id,name,effort,other_cost FROM products_old");
            db.execSQL("INSERT INTO product_materials (id,product_id,material_id,qty) SELECT id,product_id,material_id,qty FROM product_materials_old");
            db.execSQL("DROP TABLE product_materials_old");
            db.execSQL("DROP TABLE products_old");
        }
    }'''
if old_upgrade in db:
    db = db.replace(old_upgrade, new_upgrade)
elif 'if (oldVersion < 2)' not in db:
    raise SystemExit('Expected onUpgrade method was not found')

db_path.write_text(db, encoding='utf-8')

gradle = gradle_path.read_text(encoding='utf-8')
gradle = gradle.replace('versionCode 3', 'versionCode 4')
gradle = gradle.replace("versionName '1.0.2'", "versionName '1.0.3'")
gradle_path.write_text(gradle, encoding='utf-8')

seed = json.loads(seed_path.read_text(encoding='utf-8'))
material_names = {m['name'].strip().casefold() for m in seed['materials']}
missing = []
for product in seed['products']:
    for usage in product['materials']:
        if usage['material'].strip().casefold() not in material_names:
            missing.append((product['name'], usage['material']))
if missing:
    raise SystemExit(f'Missing material references: {missing}')

# Duplicate product names are intentionally supported. The original crash came
# from enforcing UNIQUE while the supplied seed legitimately contains two
# entries named Gerbera with different costing compositions.
print('Runtime hotfix applied: product names are non-unique; DB v2; app v1.0.3')
