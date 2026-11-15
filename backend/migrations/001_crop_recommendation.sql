-- Crop recommendation support (task.md).
--
-- OPTIONAL. The application already runs without this migration: the values
-- below exist as defaults in backend/app/services/crop_defaults.py. Run this in
-- the Supabase SQL editor only when you want to override them per crop, since
-- any column present in the database takes precedence over the code default.
--
-- The scoring weights are fixed application rules applied to every eligible
-- crop, so they are held in code and deliberately not stored here.
--
-- Values seeded below are APPLICATION DEFAULTS, not validated agronomy.

-- 1. Crop tolerance limits -------------------------------------------------
-- Each factor keeps its existing single optimum. Scoring is 1.0 at the optimum
-- and falls linearly to 0 at these limits, so both shortage and excess reduce
-- suitability.
alter table crops add column if not exists tol_temperature_min_c   numeric;
alter table crops add column if not exists tol_temperature_max_c   numeric;
alter table crops add column if not exists tol_soil_moisture_min   numeric;
alter table crops add column if not exists tol_soil_moisture_max   numeric;
alter table crops add column if not exists tol_ph_min              numeric;
alter table crops add column if not exists tol_ph_max              numeric;
alter table crops add column if not exists tol_humidity_min        numeric;
alter table crops add column if not exists tol_humidity_max        numeric;
alter table crops add column if not exists tol_nutrients_min       numeric;
alter table crops add column if not exists tol_nutrients_max       numeric;

-- Default tolerance bands, applied symmetrically around each optimum.
-- Edit individual crops afterwards where a tighter or wider band is known.
update crops set
    tol_temperature_min_c = optimal_temperature_c - 10,
    tol_temperature_max_c = optimal_temperature_c + 10,
    tol_soil_moisture_min = greatest(optimal_soil_moisture - 12.5, 0),
    tol_soil_moisture_max = optimal_soil_moisture + 12.5,
    tol_ph_min            = greatest(optimal_ph - 1.5, 0),
    tol_ph_max            = optimal_ph + 1.5,
    tol_humidity_min      = greatest(optimal_humidity - 25, 0),
    tol_humidity_max      = least(optimal_humidity + 25, 100),
    tol_nutrients_min     = greatest(optimal_nutrients - 0.8, 0),
    tol_nutrients_max     = optimal_nutrients + 0.8
where tol_temperature_min_c is null;

-- 2. Planting capacity -----------------------------------------------------
-- Ground area one plant occupies, in square metres.
alter table crops add column if not exists area_per_plant_m2 numeric;

update crops set area_per_plant_m2 = case name
    when 'Apple'          then 20
    when 'Orange'         then 20
    when 'Peach'          then 20
    when 'Pear'           then 20
    when 'Cherry'         then 25
    when 'Plum'           then 20
    when 'Apricot'        then 20
    when 'Lemon'          then 16
    when 'Grapefruit'     then 20
    when 'Avocado'        then 25
    when 'Almond'         then 25
    when 'Fig'            then 20
    when 'Pomegranate'    then 12
    when 'Grape'          then 4
    when 'Blueberry'      then 2.5
    when 'Blackberry'     then 2
    when 'Raspberry'      then 1.5
    when 'Cranberry'      then 1
    when 'Pineapple'      then 0.6
    when 'Watermelon'     then 3
    when 'Cantaloupe'     then 2
    when 'Zucchini'       then 1
    when 'Cucumber'       then 0.5
    when 'Tomato'         then 0.5
    when 'Broccoli'       then 0.25
    when 'Sweet Corn'     then 0.25
    when 'Kale'           then 0.25
    when 'Strawberry'     then 0.15
    when 'Bush Bean'      then 0.1
    when 'Peas'           then 0.1
    when 'Mustard Greens' then 0.1
    when 'Lettuce'        then 0.09
    when 'Spinach'        then 0.06
    when 'Beet'           then 0.02
    when 'Carrot'         then 0.01
    when 'Radish'         then 0.01
end
where area_per_plant_m2 is null;

-- 3. Soil type compatibility ----------------------------------------------
-- optimal_soil_texture holds one class. Measured soil is classified into a USDA
-- texture class, so each crop needs the explicit set of classes it accepts.
alter table crops add column if not exists compatible_soil_textures text[];

update crops set compatible_soil_textures = case optimal_soil_texture
    when 'Loam' then array[
        'Loam', 'Silt Loam', 'Clay Loam', 'Silty Clay Loam', 'Sandy Clay Loam'
    ]
    when 'Sandy Loam' then array[
        'Sandy Loam', 'Loamy Sand', 'Loam', 'Sandy Clay Loam'
    ]
    else array[optimal_soil_texture]
end
where compatible_soil_textures is null;

-- 4. Planting history ------------------------------------------------------
-- Existing identifiers, relationships and dates are preserved; these record the
-- crop name and demand category as they were when the planting happened.
alter table planting_history add column if not exists plant_name           text;
alter table planting_history add column if not exists soil_nutrition_demand text;

update planting_history h
set plant_name            = c.name,
    soil_nutrition_demand = c.soil_nutrient_demand
from crops c
where h.crop_id = c.id
  and (h.plant_name is null or h.soil_nutrition_demand is null);
