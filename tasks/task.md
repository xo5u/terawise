S = 0.17 X SM  + 0.17 * t + 0.13 X ST + 0.13 X NU + 0.11 X PH + 0.11 x AH + 0.18 WR

soile mostuol tempreture , soile type , nuturns (Nitrogen) + ph + air humidty + water requremnt 


Each attribute will be given by dividing the perfect (desired)/reading attribute from API then multiply each one with the impact factor from the DB,
each impact facotr represent the of the most important facotr that affecct the plants by its percentage and 
at the end we will get the top 3 from suitabilty calcualtion.

for nitrogen (obtemal_nutrise)- nitrogen  if nitrogen is less than optimal else dont do anything then we will divide with the result on the 
furtilzer type DB to identify the suitable amount of furtilizer

notice if the plant in the H in soil_nutration_demand in db do not give us any H 

the m will get piorty 2
the l will get priorty 1 
1 is hightst
2 if no low is there

also for the M only plant the low ones
and if and only if there are no low plant aka L use the M 

if the plant dont match the soile ignore it 

the resluts will be shown for the next months on the DB of the growth to give fruit or vegtable

also display the amount of water needed for the area we enterd of the farm, we will make a std land size for each plant then
multi the the amount for each plant needed across the whole size of the farm, on the result.

also the amount of the water is seasonal now for 4 months can be extraced from DB so like if the plant need 30 month from we wll see 
how many season in there and calc the required water from 

here if the seaion more than 4 month we will use this requr scale up (month / 4) the reuslt will multible my water amouunt  

now for the rainfall calc we will take Rainfall from API x Area x Benift from rain (assume always 80%) then we will see the reuslt will added to the 
water amount 
if the total water amount ( tank + rain ) < requrmnt do not need it 
example 
if rain will help by 5l and the tank cas suppourt for 4 month bu 50l total amput will be 55L here we will compere by each plant requrmnt 


edit in the UI to make the plants options same as the one from the DB 
make the water source to tank 
the proft change it to amount of water in the tank 

now for the history we want to see the last 1 or two at max crops a





