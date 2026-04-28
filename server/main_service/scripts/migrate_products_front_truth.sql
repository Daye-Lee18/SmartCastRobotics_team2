-- Product 테이블을 프론트 (src/app/customer/page.tsx PRODUCTS) 기준으로 재정렬
-- 실행: psql $DATABASE_URL -f backend/scripts/migrate_products_front_truth.sql
-- 2026-04-09, 멱등 실행 가능

BEGIN;

-- 1. 컬럼 추가 (IF NOT EXISTS 로 재실행 안전)
ALTER TABLE products ADD COLUMN IF NOT EXISTS category_label        VARCHAR NOT NULL DEFAULT '';
ALTER TABLE products ADD COLUMN IF NOT EXISTS spec                  VARCHAR NOT NULL DEFAULT '';
ALTER TABLE products ADD COLUMN IF NOT EXISTS price_range           VARCHAR NOT NULL DEFAULT '';
ALTER TABLE products ADD COLUMN IF NOT EXISTS diameter_options_json TEXT    NOT NULL DEFAULT '[]';
ALTER TABLE products ADD COLUMN IF NOT EXISTS thickness_options_json TEXT   NOT NULL DEFAULT '[]';
ALTER TABLE products ADD COLUMN IF NOT EXISTS materials_json        TEXT    NOT NULL DEFAULT '[]';
ALTER TABLE products ADD COLUMN IF NOT EXISTS load_class_range      VARCHAR NOT NULL DEFAULT '';

-- 2. order_details.product_id 매핑 (기존 PRD-XXX → 프론트식 도메인 ID)
UPDATE order_details SET product_id = 'D600'    WHERE product_id = 'PRD-001';
UPDATE order_details SET product_id = 'D800'    WHERE product_id = 'PRD-002';
UPDATE order_details SET product_id = 'D450'    WHERE product_id = 'PRD-003';
UPDATE order_details SET product_id = 'D450'    WHERE product_id = 'PRD-004';  -- 빗물받이 → D450 매핑 (가장 가까운 맨홀)
UPDATE order_details SET product_id = 'GRATING' WHERE product_id = 'PRD-005';

-- 3. 기존 5개 row 전부 삭제 (PRD-XXX id 로 저장된 데이터)
DELETE FROM products;

-- 4. 프론트 기준 4개 제품 insert
INSERT INTO products (
    id, name, category, category_label, spec, price_range, base_price,
    diameter_options_json, thickness_options_json, materials_json, load_class_range,
    option_pricing_json, design_image_url, model_3d_path
) VALUES
(
    'D450', '맨홀 뚜껑 KS D-450', 'manhole', '맨홀 뚜껑',
    '직경 450mm, KS 규격', '50,000 - 70,000원', 55000,
    '["450mm","460mm","470mm"]',
    '["25mm","30mm","35mm","40mm"]',
    '["FC200","FC250","GCD450"]',
    'B125 ~ D400',
    '{"표면 연마":3000,"방청 코팅":2000}',
    '/images/products/manhole-450.png',
    '/models/manhole-450.glb'
),
(
    'D600', '맨홀 뚜껑 KS D-600', 'manhole', '맨홀 뚜껑',
    '직경 600mm, KS 규격', '75,000 - 100,000원', 85000,
    '["600mm","610mm","620mm"]',
    '["30mm","35mm","40mm","45mm"]',
    '["FC200","FC250","GCD450","GCD500"]',
    'B125 ~ F900',
    '{"표면 연마":5000,"방청 코팅":3000,"로고 삽입":8000}',
    '/images/products/manhole-600.png',
    '/models/manhole-600.glb'
),
(
    'D800', '맨홀 뚜껑 KS D-800', 'manhole', '맨홀 뚜껑',
    '직경 800mm, KS 규격', '110,000 - 140,000원', 120000,
    '["800mm","810mm","820mm"]',
    '["35mm","40mm","45mm","50mm"]',
    '["FC250","GCD450","GCD500"]',
    'C250 ~ F900',
    '{"표면 연마":7000,"방청 코팅":4000,"로고 삽입":10000}',
    '/images/products/manhole-800.png',
    '/models/manhole-800.glb'
),
(
    'GRATING', '배수구 그레이팅 500x300', 'grating', '그레이팅',
    '500x300mm, 격자형', '30,000 - 45,000원', 35000,
    '["500x300mm","500x350mm","600x300mm"]',
    '["20mm","25mm","30mm"]',
    '["FC200","FC250"]',
    'B125 ~ C250',
    '{"아연 도금":5000,"내식 코팅":7000}',
    '/images/products/grating-500.png',
    '/models/grating-500.glb'
);

COMMIT;
