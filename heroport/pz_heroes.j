//@GLOBALS
hashtable PZH=InitHashtable()
group PZHeroes=CreateGroup()
group PZG1=CreateGroup()
group PZG2=CreateGroup()
group PZG3=CreateGroup()
group PZG4=CreateGroup()
timer PZClock=CreateTimer()
trigger PZBulwarkTrig=null
unit PZHarv=null
rect PZRect=null
real PZMinX=0.
real PZMinY=0.
real PZMaxX=0.
real PZMaxY=0.
real PZFX=0.
real PZFY=0.
real PZFDD=0.
destructable PZFD=null
integer PZRandChance=25
integer PZPickTest=0
boolean PZDebug=false
real array PZThreat
group PZG5=CreateGroup()
//@FUNCS
function PZNow takes nothing returns real
return TimerGetElapsed(PZClock)
endfunction
function PZLog takes string pzS returns nothing
if PZDebug then
call DisplayTimedTextToPlayer(GetLocalPlayer(),0.,0.,20.,"|cff00ff00[PZ "+I2S(R2I(PZNow()))+"]|r "+pzS)
endif
endfunction
function PZCount takes unit pzU,integer pzKey returns nothing
call SaveInteger(PZH,GetHandleId(pzU),pzKey,LoadInteger(PZH,GetHandleId(pzU),pzKey)+1)
endfunction
function PZCX takes real pzX returns real
if pzX<PZMinX then
return PZMinX
elseif pzX>PZMaxX then
return PZMaxX
endif
return pzX
endfunction
function PZCY takes real pzY returns real
if pzY<PZMinY then
return PZMinY
elseif pzY>PZMaxY then
return PZMaxY
endif
return pzY
endfunction
function PZFxEnd takes nothing returns nothing
local timer pzT=GetExpiredTimer()
call DestroyEffect(LoadEffectHandle(PZH,GetHandleId(pzT),0))
call FlushChildHashtable(PZH,GetHandleId(pzT))
call DestroyTimer(pzT)
set pzT=null
endfunction
function PZFxKeep takes effect pzE,real pzD returns nothing
local timer pzT=CreateTimer()
call SaveEffectHandle(PZH,GetHandleId(pzT),0,pzE)
call TimerStart(pzT,pzD,false,function PZFxEnd)
set pzT=null
endfunction
function PZFx takes string pzM,real pzX,real pzY,real pzD returns nothing
if pzD<=0. then
call DestroyEffect(AddSpecialEffect(pzM,pzX,pzY))
else
call PZFxKeep(AddSpecialEffect(pzM,pzX,pzY),pzD)
endif
endfunction
function PZFxOn takes string pzM,unit pzU,string pzA,real pzD returns nothing
if pzD<=0. then
call DestroyEffect(AddSpecialEffectTarget(pzM,pzU,pzA))
else
call PZFxKeep(AddSpecialEffectTarget(pzM,pzU,pzA),pzD)
endif
endfunction
function PZAlive takes unit pzU returns boolean
return pzU!=null and GetWidgetLife(pzU)>0.405 and not IsUnitType(pzU,UNIT_TYPE_DEAD)
endfunction
function PZIsFoe takes unit pzS,unit pzT returns boolean
return PZAlive(pzT) and IsUnitEnemy(pzT,GetOwningPlayer(pzS)) and not IsUnitType(pzT,UNIT_TYPE_STRUCTURE) and GetUnitAbilityLevel(pzT,'Aloc')==0 and GetUnitAbilityLevel(pzT,'Avul')==0
endfunction
function PZIsFoeHero takes unit pzS,unit pzT returns boolean
return PZIsFoe(pzS,pzT) and IsUnitType(pzT,UNIT_TYPE_HERO) and IsUnitVisible(pzT,GetOwningPlayer(pzS))
endfunction
function PZAtk takes unit pzU returns real
if GetUnitTypeId(pzU)=='HMRS' then
return 33.+GetHeroStr(pzU,true)
endif
return 32.+GetHeroAgi(pzU,true)
endfunction
function PZDmgMagic takes unit pzS,unit pzT,real pzA returns nothing
call UnitDamageTarget(pzS,pzT,pzA,true,false,ATTACK_TYPE_NORMAL,DAMAGE_TYPE_MAGIC,WEAPON_TYPE_WHOKNOWS)
endfunction
function PZDmgPhys takes unit pzS,unit pzT,real pzA returns nothing
call UnitDamageTarget(pzS,pzT,pzA,true,false,ATTACK_TYPE_HERO,DAMAGE_TYPE_NORMAL,WEAPON_TYPE_WHOKNOWS)
endfunction
function PZCaster takes player pzP,real pzX,real pzY returns unit
local unit pzU=CreateUnit(pzP,'eZ01',PZCX(pzX),PZCY(pzY),0.)
call UnitApplyTimedLife(pzU,'BTLF',2.)
set bj_lastCreatedUnit=pzU
set pzU=null
return bj_lastCreatedUnit
endfunction
function PZStunBy takes player pzP,unit pzT,real pzD returns nothing
local integer pzL=R2I(pzD*10.+0.5)
local unit pzU
if pzL<1 then
set pzL=1
elseif pzL>40 then
set pzL=40
endif
set pzU=PZCaster(pzP,GetUnitX(pzT),GetUnitY(pzT))
call UnitAddAbility(pzU,'AZ14')
call SetUnitAbilityLevel(pzU,'AZ14',pzL)
call IssueTargetOrder(pzU,"thunderbolt",pzT)
set pzU=null
endfunction
function PZStun takes unit pzS,unit pzT,real pzD returns nothing
call PZStunBy(GetOwningPlayer(pzS),pzT,pzD)
endfunction
function PZSlow takes unit pzS,unit pzT,integer pzL returns nothing
local unit pzU
if pzL<1 then
return
endif
set pzU=PZCaster(GetOwningPlayer(pzS),GetUnitX(pzT),GetUnitY(pzT))
call UnitAddAbility(pzU,'AZ15')
call SetUnitAbilityLevel(pzU,'AZ15',pzL)
call IssueTargetOrder(pzU,"slow",pzT)
set pzU=null
endfunction
function PZKnockTick takes nothing returns nothing
local timer pzT=GetExpiredTimer()
local integer pzK=GetHandleId(pzT)
local unit pzU=LoadUnitHandle(PZH,pzK,0)
local integer pzN=LoadInteger(PZH,pzK,3)-1
local real pzX=GetUnitX(pzU)+LoadReal(PZH,pzK,1)
local real pzY=GetUnitY(pzU)+LoadReal(PZH,pzK,2)
if pzN<0 or not PZAlive(pzU) then
call FlushChildHashtable(PZH,pzK)
call DestroyTimer(pzT)
else
if not IsTerrainPathable(pzX,pzY,PATHING_TYPE_WALKABILITY) then
call SetUnitX(pzU,PZCX(pzX))
call SetUnitY(pzU,PZCY(pzY))
endif
call SaveInteger(PZH,pzK,3,pzN)
endif
set pzT=null
set pzU=null
endfunction
function PZKnock takes unit pzU,real pzA,real pzDist,real pzDur returns nothing
local timer pzT=CreateTimer()
local integer pzK=GetHandleId(pzT)
local integer pzN=R2I(pzDur/0.03)
if pzN<1 then
set pzN=1
endif
call SaveUnitHandle(PZH,pzK,0,pzU)
call SaveReal(PZH,pzK,1,pzDist/pzN*Cos(pzA))
call SaveReal(PZH,pzK,2,pzDist/pzN*Sin(pzA))
call SaveInteger(PZH,pzK,3,pzN)
call TimerStart(pzT,0.03,true,function PZKnockTick)
set pzT=null
endfunction
function PZIsTree takes destructable pzD returns boolean
local integer pzK=GetHandleId(pzD)
local boolean pzB
if HaveSavedBoolean(PZH,pzK,7) then
return LoadBoolean(PZH,pzK,7)
endif
set pzB=IssueTargetOrderById(PZHarv,852018,pzD)
call IssueImmediateOrderById(PZHarv,851972)
call SaveBoolean(PZH,pzK,7,pzB)
return pzB
endfunction
function PZTreeEnum takes nothing returns nothing
local destructable pzD=GetEnumDestructable()
local real pzDX=GetDestructableX(pzD)-PZFX
local real pzDY=GetDestructableY(pzD)-PZFY
local real pzR=pzDX*pzDX+pzDY*pzDY
if pzR<PZFDD and GetDestructableLife(pzD)>0.405 and PZIsTree(pzD) then
set PZFDD=pzR
set PZFD=pzD
endif
set pzD=null
endfunction
function PZNearestTree takes real pzX,real pzY,real pzRad returns destructable
set PZFX=pzX
set PZFY=pzY
set PZFD=null
set PZFDD=pzRad*pzRad
call SetRect(PZRect,pzX-pzRad,pzY-pzRad,pzX+pzRad,pzY+pzRad)
call EnumDestructablesInRect(PZRect,null,function PZTreeEnum)
return PZFD
endfunction
function PZReadyAt takes unit pzU,integer pzA returns real
return LoadReal(PZH,GetHandleId(pzU),pzA)
endfunction
function PZCooldown takes integer pzA,integer pzL returns real
if pzA=='AZ02' then
return 22.
elseif pzA=='AZ04' then
return 21.-2.*pzL
elseif pzA=='AZ08' then
return 150.-20.*pzL
elseif pzA=='AZ10' then
return 14.
elseif pzA=='AZ11' then
return 18.-2.*pzL
elseif pzA=='AZ13' then
return 105.-15.*pzL
endif
return 1.
endfunction
// ---------------- Monkey King: Boundless Strike
function PZBoundless takes unit pzU,real pzTX,real pzTY returns nothing
local real pzX=GetUnitX(pzU)
local real pzY=GetUnitY(pzU)
local real pzA=Atan2(pzTY-pzY,pzTX-pzX)
local integer pzL=GetUnitAbilityLevel(pzU,'AZ02')
local real pzDmg=PZAtk(pzU)*(1.25+0.25*pzL)
local real pzSt=0.4+0.3*pzL
local real pzC=Cos(pzA)
local real pzS=Sin(pzA)
local real pzRX
local real pzRY
local real pzP
local real pzQ
local integer pzI=0
local unit pzT
loop
exitwhen pzI>11
call PZFx("H\\MK\\HeroMonkeyking_Q_blast.mdx",PZCX(pzX+pzC*pzI*100.),PZCY(pzY+pzS*pzI*100.),0.)
set pzI=pzI+1
endloop
call GroupEnumUnitsInRange(PZG1,pzX+pzC*600.,pzY+pzS*600.,800.,null)
loop
set pzT=FirstOfGroup(PZG1)
exitwhen pzT==null
call GroupRemoveUnit(PZG1,pzT)
if PZIsFoe(pzU,pzT) and not IsUnitType(pzT,UNIT_TYPE_MAGIC_IMMUNE) then
set pzRX=GetUnitX(pzT)-pzX
set pzRY=GetUnitY(pzT)-pzY
set pzP=pzRX*pzC+pzRY*pzS
set pzQ=pzRX*pzS-pzRY*pzC
if pzP>=-75. and pzP<=1175. and pzQ<=175. and pzQ>=-175. then
call PZStun(pzU,pzT,pzSt)
call PZDmgPhys(pzU,pzT,pzDmg)
endif
endif
endloop
endfunction
// ---------------- Monkey King: Tree Dance / Primal Spring
function PZSetSpringAvail takes unit pzU,boolean pzB returns nothing
if GetUnitAbilityLevel(pzU,'AZ04')>0 then
call SetPlayerAbilityAvailable(GetOwningPlayer(pzU),'AZ04',pzB)
endif
endfunction
function PZUnperch takes unit pzU returns nothing
local integer pzK=GetHandleId(pzU)
call SaveBoolean(PZH,pzK,10,false)
call SaveBoolean(PZH,pzK,14,false)
call SetUnitFlyHeight(pzU,0.,0.)
call SetUnitPathing(pzU,true)
call SetUnitPosition(pzU,GetUnitX(pzU),GetUnitY(pzU))
call PZSetSpringAvail(pzU,false)
endfunction
function PZSpringLand takes unit pzU,integer pzL,real pzF returns nothing
local real pzX=GetUnitX(pzU)
local real pzY=GetUnitY(pzU)
local real pzDmg=(70.+70.*pzL)*pzF
local integer pzSl=R2I(2.*pzL*pzF+0.5)
local unit pzT
call PZFx("H\\MK\\JumpAoE.mdx",pzX,pzY,0.)
call PZFx("H\\MK\\HeroMonkeyking_W3_Gather.mdx",pzX,pzY,0.)
call GroupEnumUnitsInRange(PZG2,pzX,pzY,375.,null)
loop
set pzT=FirstOfGroup(PZG2)
exitwhen pzT==null
call GroupRemoveUnit(PZG2,pzT)
if PZIsFoe(pzU,pzT) and not IsUnitType(pzT,UNIT_TYPE_MAGIC_IMMUNE) then
call PZDmgMagic(pzU,pzT,pzDmg)
call PZSlow(pzU,pzT,pzSl)
endif
endloop
endfunction
function PZLeapTick takes nothing returns nothing
local timer pzT=GetExpiredTimer()
local integer pzK=GetHandleId(pzT)
local unit pzU=LoadUnitHandle(PZH,pzK,0)
local integer pzN=LoadInteger(PZH,pzK,9)+1
local integer pzM=LoadInteger(PZH,pzK,8)
local real pzR=I2R(pzN)/I2R(pzM)
local real pzX=LoadReal(PZH,pzK,1)+(LoadReal(PZH,pzK,3)-LoadReal(PZH,pzK,1))*pzR
local real pzY=LoadReal(PZH,pzK,2)+(LoadReal(PZH,pzK,4)-LoadReal(PZH,pzK,2))*pzR
local real pzH=LoadReal(PZH,pzK,5)+(LoadReal(PZH,pzK,6)-LoadReal(PZH,pzK,5))*pzR+LoadReal(PZH,pzK,7)*4.*pzR*(1.-pzR)
local integer pzMode=LoadInteger(PZH,pzK,10)
local integer pzUK=GetHandleId(pzU)
if not PZAlive(pzU) then
call SaveBoolean(PZH,pzUK,14,false)
call PZUnperch(pzU)
call FlushChildHashtable(PZH,pzK)
call DestroyTimer(pzT)
set pzT=null
set pzU=null
return
endif
call SetUnitX(pzU,PZCX(pzX))
call SetUnitY(pzU,PZCY(pzY))
call SetUnitFlyHeight(pzU,pzH,0.)
call SaveInteger(PZH,pzK,9,pzN)
if pzN>=pzM then
call SaveBoolean(PZH,pzUK,14,false)
if pzMode==1 then
call SaveBoolean(PZH,pzUK,10,true)
call SaveReal(PZH,pzUK,12,pzX)
call SaveReal(PZH,pzUK,13,pzY)
call PZSetSpringAvail(pzU,true)
call PZFx("H\\MK\\HeroMonkeyking_W2_circle.mdx",pzX,pzY,0.)
else
call PZUnperch(pzU)
call PZSpringLand(pzU,LoadInteger(PZH,pzK,11),LoadReal(PZH,pzK,12))
endif
call FlushChildHashtable(PZH,pzK)
call DestroyTimer(pzT)
endif
set pzT=null
set pzU=null
endfunction
function PZLeap takes unit pzU,real pzEX,real pzEY,real pzEH,real pzArc,real pzSpeed,integer pzMode returns timer
local timer pzT=CreateTimer()
local integer pzK=GetHandleId(pzT)
local real pzSX=GetUnitX(pzU)
local real pzSY=GetUnitY(pzU)
local real pzD=SquareRoot((pzEX-pzSX)*(pzEX-pzSX)+(pzEY-pzSY)*(pzEY-pzSY))
local integer pzM=R2I(pzD/pzSpeed/0.03)
if pzM<8 then
set pzM=8
endif
call SaveBoolean(PZH,GetHandleId(pzU),14,true)
call SetUnitPathing(pzU,false)
call SetUnitFacing(pzU,Atan2(pzEY-pzSY,pzEX-pzSX)*bj_RADTODEG)
call SaveUnitHandle(PZH,pzK,0,pzU)
call SaveReal(PZH,pzK,1,pzSX)
call SaveReal(PZH,pzK,2,pzSY)
call SaveReal(PZH,pzK,3,pzEX)
call SaveReal(PZH,pzK,4,pzEY)
call SaveReal(PZH,pzK,5,GetUnitFlyHeight(pzU))
call SaveReal(PZH,pzK,6,pzEH)
call SaveReal(PZH,pzK,7,pzArc)
call SaveInteger(PZH,pzK,8,pzM)
call SaveInteger(PZH,pzK,9,0)
call SaveInteger(PZH,pzK,10,pzMode)
call TimerStart(pzT,0.03,true,function PZLeapTick)
set bj_lastStartedTimer=pzT
set pzT=null
return bj_lastStartedTimer
endfunction
function PZTreeDance takes unit pzU,real pzTX,real pzTY returns nothing
local destructable pzD=PZNearestTree(pzTX,pzTY,250.)
local integer pzK=GetHandleId(pzU)
if pzD==null then
if GetLocalPlayer()==GetOwningPlayer(pzU) then
call DisplayTimedTextToPlayer(GetLocalPlayer(),0.,0.,2.,"|cffffcc00Tree Dance:|r target a tree.")
endif
return
endif
call SaveDestructableHandle(PZH,pzK,11,pzD)
call PZFx("H\\MK\\HeroMonkeyking_W1.mdx",GetUnitX(pzU),GetUnitY(pzU),0.)
call PZLeap(pzU,GetDestructableX(pzD),GetDestructableY(pzD),220.,150.,1100.,1)
set pzD=null
endfunction
function PZSpringStart takes unit pzU,real pzTX,real pzTY returns nothing
local integer pzK=GetHandleId(pzU)
call SaveReal(PZH,pzK,20,PZNow())
call SaveReal(PZH,pzK,21,pzTX)
call SaveReal(PZH,pzK,22,pzTY)
call SaveEffectHandle(PZH,pzK,23,AddSpecialEffect("H\\MK\\HeroMonkeyking_W2_circle.mdx",pzTX,pzTY))
endfunction
function PZSpringEnd takes unit pzU returns nothing
local integer pzK=GetHandleId(pzU)
local real pzF=(PZNow()-LoadReal(PZH,pzK,20))/1.6
local real pzX=GetUnitX(pzU)
local real pzY=GetUnitY(pzU)
local real pzTX=LoadReal(PZH,pzK,21)
local real pzTY=LoadReal(PZH,pzK,22)
local real pzD=SquareRoot((pzTX-pzX)*(pzTX-pzX)+(pzTY-pzY)*(pzTY-pzY))
local timer pzT
call DestroyEffect(LoadEffectHandle(PZH,pzK,23))
call RemoveSavedHandle(PZH,pzK,23)
if not LoadBoolean(PZH,pzK,10) or not PZAlive(pzU) then
return
endif
if pzF>1. then
set pzF=1.
elseif pzF<0.15 then
set pzF=0.15
endif
if pzD>1100. then
set pzTX=pzX+(pzTX-pzX)*1100./pzD
set pzTY=pzY+(pzTY-pzY)*1100./pzD
endif
call SaveBoolean(PZH,pzK,10,false)
call PZSetSpringAvail(pzU,false)
set pzT=PZLeap(pzU,PZCX(pzTX),PZCY(pzTY),0.,200.,1400.,2)
call SaveInteger(PZH,GetHandleId(pzT),11,GetUnitAbilityLevel(pzU,'AZ04'))
call SaveReal(PZH,GetHandleId(pzT),12,pzF)
set pzT=null
endfunction
// ---------------- Monkey King: Jingu Mastery
function PZJinguOff takes unit pzU returns nothing
local integer pzK=GetHandleId(pzU)
call SaveInteger(PZH,pzK,30,0)
call UnitRemoveAbility(pzU,'AZ06')
call UnitRemoveAbility(pzU,'AZ07')
call DestroyEffect(LoadEffectHandle(PZH,pzK,32))
call RemoveSavedHandle(PZH,pzK,32)
endfunction
function PZJinguAttack takes unit pzU,unit pzT returns nothing
local integer pzK=GetHandleId(pzU)
local integer pzC=LoadInteger(PZH,pzK,30)
local integer pzTK
local integer pzN
local integer pzL=GetUnitAbilityLevel(pzU,'AZ05')
if pzC>0 then
set pzC=pzC-1
call SaveInteger(PZH,pzK,30,pzC)
if pzC==0 then
call SaveReal(PZH,pzK,31,PZNow()+0.75)
else
call SaveReal(PZH,pzK,31,PZNow()+10.)
endif
return
endif
if not IsUnitType(pzT,UNIT_TYPE_HERO) or IsUnitIllusion(pzT) or not IsUnitEnemy(pzT,GetOwningPlayer(pzU)) then
return
endif
set pzTK=GetHandleId(pzT)
set pzN=LoadInteger(PZH,pzTK,pzK)
if PZNow()-LoadReal(PZH,pzTK,-pzK)>35. then
set pzN=0
endif
set pzN=pzN+1
call SaveReal(PZH,pzTK,-pzK,PZNow())
if pzN>=4 then
call PZCount(pzU,52)
call PZLog("Jingu Mastery charged on "+GetUnitName(pzT))
call SaveInteger(PZH,pzTK,pzK,0)
call SaveInteger(PZH,pzK,30,4)
call SaveReal(PZH,pzK,31,PZNow()+10.)
call UnitAddAbility(pzU,'AZ06')
call SetUnitAbilityLevel(pzU,'AZ06',pzL)
call UnitAddAbility(pzU,'AZ07')
call SetUnitAbilityLevel(pzU,'AZ07',pzL)
call DestroyEffect(LoadEffectHandle(PZH,pzK,32))
call SaveEffectHandle(PZH,pzK,32,AddSpecialEffectTarget("H\\MK\\HeroMonkeyking_E_hand_Buff.mdx",pzU,"weapon"))
call PZFxOn("H\\MK\\HeroMonkeyking_E_Impact.mdx",pzT,"chest",0.)
else
call SaveInteger(PZH,pzTK,pzK,pzN)
call PZFxOn("H\\MK\\HeroMonkeyking_E_DeBuff"+I2S(pzN)+".mdx",pzT,"overhead",2.)
endif
endfunction
// ---------------- Monkey King: Wukong's Command
function PZWukongEnd takes timer pzT returns nothing
local integer pzK=GetHandleId(pzT)
local unit pzU=LoadUnitHandle(PZH,pzK,0)
local group pzG=LoadGroupHandle(PZH,pzK,5)
local unit pzS
loop
set pzS=FirstOfGroup(pzG)
exitwhen pzS==null
call GroupRemoveUnit(pzG,pzS)
call PZFx("H\\MK\\HeroMonkeyking_R_End.mdx",GetUnitX(pzS),GetUnitY(pzS),0.)
call FlushChildHashtable(PZH,GetHandleId(pzS))
call RemoveUnit(pzS)
endloop
call DestroyGroup(pzG)
call DestroyEffect(LoadEffectHandle(PZH,pzK,6))
call UnitRemoveAbility(pzU,'AZ09')
if LoadTimerHandle(PZH,GetHandleId(pzU),40)==pzT then
call RemoveSavedHandle(PZH,GetHandleId(pzU),40)
endif
call FlushChildHashtable(PZH,pzK)
call DestroyTimer(pzT)
set pzU=null
set pzG=null
endfunction
function PZWukongTick takes nothing returns nothing
local timer pzT=GetExpiredTimer()
local integer pzK=GetHandleId(pzT)
local unit pzU=LoadUnitHandle(PZH,pzK,0)
local real pzCX=LoadReal(PZH,pzK,1)
local real pzCY=LoadReal(PZH,pzK,2)
local group pzG=LoadGroupHandle(PZH,pzK,5)
local real pzNow=PZNow()
local real pzDX=GetUnitX(pzU)-pzCX
local real pzDY=GetUnitY(pzU)-pzCY
local unit pzS
local unit pzT2
local unit pzBest
local real pzBD
local real pzR
local integer pzI=0
local integer pzN
if not PZAlive(pzU) or pzNow>=LoadReal(PZH,pzK,3) or pzDX*pzDX+pzDY*pzDY>1100.*1100. then
call PZWukongEnd(pzT)
set pzT=null
set pzU=null
set pzG=null
return
endif
if GetUnitAbilityLevel(pzU,'AZ09')==0 then
call UnitAddAbility(pzU,'AZ09')
call SetUnitAbilityLevel(pzU,'AZ09',LoadInteger(PZH,pzK,4))
endif
set pzN=CountUnitsInGroup(pzG)
loop
exitwhen pzI>=pzN
set pzS=LoadUnitHandle(PZH,pzK,100+pzI)
if pzS!=null and pzNow>=LoadReal(PZH,GetHandleId(pzS),0) then
set pzBest=null
set pzBD=325.*325.
call GroupEnumUnitsInRange(PZG3,GetUnitX(pzS),GetUnitY(pzS),325.,null)
loop
set pzT2=FirstOfGroup(PZG3)
exitwhen pzT2==null
call GroupRemoveUnit(PZG3,pzT2)
if PZIsFoeHero(pzU,pzT2) then
set pzR=(GetUnitX(pzT2)-GetUnitX(pzS))*(GetUnitX(pzT2)-GetUnitX(pzS))+(GetUnitY(pzT2)-GetUnitY(pzS))*(GetUnitY(pzT2)-GetUnitY(pzS))
if pzR<pzBD then
set pzBD=pzR
set pzBest=pzT2
endif
endif
endloop
if pzBest!=null then
call SetUnitFacing(pzS,Atan2(GetUnitY(pzBest)-GetUnitY(pzS),GetUnitX(pzBest)-GetUnitX(pzS))*bj_RADTODEG)
call SetUnitAnimation(pzS,"attack")
call QueueUnitAnimation(pzS,"stand")
call PZDmgPhys(pzU,pzBest,PZAtk(pzU))
call PZCount(pzU,54)
call PZFxOn("H\\MK\\HeroMonkeyking_E_Impact.mdx",pzBest,"chest",0.)
call SaveReal(PZH,GetHandleId(pzS),0,pzNow+1.1)
endif
endif
set pzI=pzI+1
endloop
set pzT=null
set pzU=null
set pzG=null
set pzS=null
set pzBest=null
endfunction
function PZWukong takes unit pzU,real pzCX,real pzCY returns nothing
local timer pzT
local integer pzK
local integer pzUK=GetHandleId(pzU)
local group pzG=CreateGroup()
local integer pzI=0
local integer pzN=0
local real pzA
local real pzX
local real pzY
local unit pzS
if LoadTimerHandle(PZH,pzUK,40)!=null then
call PZWukongEnd(LoadTimerHandle(PZH,pzUK,40))
endif
set pzT=CreateTimer()
set pzK=GetHandleId(pzT)
call SaveTimerHandle(PZH,pzUK,40,pzT)
call SaveUnitHandle(PZH,pzK,0,pzU)
call SaveReal(PZH,pzK,1,pzCX)
call SaveReal(PZH,pzK,2,pzCY)
call SaveReal(PZH,pzK,3,PZNow()+13.)
call SaveInteger(PZH,pzK,4,GetUnitAbilityLevel(pzU,'AZ08'))
call SaveGroupHandle(PZH,pzK,5,pzG)
call SaveEffectHandle(PZH,pzK,6,AddSpecialEffect("H\\MK\\HeroMonkeyking_R1_largecircle.mdx",pzCX,pzCY))
loop
exitwhen pzI>=15
if pzI<5 then
set pzA=pzI*72.*bj_DEGTORAD
set pzX=pzCX+300.*Cos(pzA)
set pzY=pzCY+300.*Sin(pzA)
else
set pzA=(pzI-5)*36.*bj_DEGTORAD
set pzX=pzCX+700.*Cos(pzA)
set pzY=pzCY+700.*Sin(pzA)
endif
if not IsTerrainPathable(pzX,pzY,PATHING_TYPE_WALKABILITY) then
set pzS=CreateUnit(GetOwningPlayer(pzU),'eZ02',PZCX(pzX),PZCY(pzY),pzA*bj_RADTODEG)
call SetUnitVertexColor(pzS,255,230,150,200)
call PZFx("H\\MK\\HeroMonkeyking_R2_Smallcircle.mdx",GetUnitX(pzS),GetUnitY(pzS),0.)
call GroupAddUnit(pzG,pzS)
call SaveUnitHandle(PZH,pzK,100+pzN,pzS)
call SaveReal(PZH,GetHandleId(pzS),0,PZNow()+0.3)
set pzN=pzN+1
endif
set pzI=pzI+1
endloop
call TimerStart(pzT,0.1,true,function PZWukongTick)
set pzT=null
set pzG=null
set pzS=null
endfunction
// ---------------- Mars: Spear of Mars
function PZSpearEnd takes timer pzT,boolean pzPinned returns nothing
local integer pzK=GetHandleId(pzT)
local unit pzSp=LoadUnitHandle(PZH,pzK,1)
if pzPinned then
call UnitApplyTimedLife(pzSp,'BTLF',2.)
else
call RemoveUnit(pzSp)
endif
call DestroyGroup(LoadGroupHandle(PZH,pzK,9))
call FlushChildHashtable(PZH,pzK)
call DestroyTimer(pzT)
set pzSp=null
endfunction
function PZSpearBlocked takes real pzX,real pzY returns boolean
local unit pzB
local boolean pzR=false
if IsTerrainPathable(pzX,pzY,PATHING_TYPE_WALKABILITY) then
return true
endif
if PZNearestTree(pzX,pzY,110.)!=null then
return true
endif
call GroupEnumUnitsInRange(PZG4,pzX,pzY,140.,null)
loop
set pzB=FirstOfGroup(PZG4)
exitwhen pzB==null
call GroupRemoveUnit(PZG4,pzB)
if IsUnitType(pzB,UNIT_TYPE_STRUCTURE) and PZAlive(pzB) then
set pzR=true
endif
endloop
return pzR
endfunction
function PZSpearTick takes nothing returns nothing
local timer pzT=GetExpiredTimer()
local integer pzK=GetHandleId(pzT)
local unit pzU=LoadUnitHandle(PZH,pzK,0)
local unit pzSp=LoadUnitHandle(PZH,pzK,1)
local real pzDX=LoadReal(PZH,pzK,2)
local real pzDY=LoadReal(PZH,pzK,3)
local real pzGone=LoadReal(PZH,pzK,4)+42.
local unit pzSk=LoadUnitHandle(PZH,pzK,6)
local integer pzL=LoadInteger(PZH,pzK,7)
local group pzHit=LoadGroupHandle(PZH,pzK,9)
local real pzX=GetUnitX(pzSp)+pzDX
local real pzY=GetUnitY(pzSp)+pzDY
local unit pzV
if pzSk!=null and PZAlive(pzSk) and PZSpearBlocked(pzX+pzDX*1.5,pzY+pzDY*1.5) then
call PZCount(pzU,53)
call PZLog("Spear of Mars pinned "+GetUnitName(pzSk))
call PZStun(pzU,pzSk,1.2+0.4*pzL)
call PZFx("Objects\\Spawnmodels\\Undead\\ImpaleTargetDust\\ImpaleTargetDust.mdl",GetUnitX(pzSk),GetUnitY(pzSk),0.)
call PZSpearEnd(pzT,true)
set pzT=null
set pzU=null
set pzSp=null
set pzSk=null
set pzHit=null
return
endif
call SetUnitX(pzSp,PZCX(pzX))
call SetUnitY(pzSp,PZCY(pzY))
call SaveReal(PZH,pzK,4,pzGone)
if pzSk!=null and PZAlive(pzSk) then
call SetUnitX(pzSk,PZCX(pzX))
call SetUnitY(pzSk,PZCY(pzY))
endif
call GroupEnumUnitsInRange(PZG4,pzX,pzY,125.,null)
loop
set pzV=FirstOfGroup(PZG4)
exitwhen pzV==null
call GroupRemoveUnit(PZG4,pzV)
if PZIsFoe(pzU,pzV) and not IsUnitInGroup(pzV,pzHit) then
call GroupAddUnit(pzHit,pzV)
call PZDmgMagic(pzU,pzV,25.+75.*pzL)
if pzSk==null and IsUnitType(pzV,UNIT_TYPE_HERO) and not IsUnitType(pzV,UNIT_TYPE_MAGIC_IMMUNE) and PZAlive(pzV) then
set pzSk=pzV
call SaveUnitHandle(PZH,pzK,6,pzV)
endif
endif
endloop
if pzGone>=LoadReal(PZH,pzK,5) then
call PZSpearEnd(pzT,false)
endif
set pzT=null
set pzU=null
set pzSp=null
set pzSk=null
set pzHit=null
set pzV=null
endfunction
function PZSpear takes unit pzU,real pzTX,real pzTY returns nothing
local timer pzT=CreateTimer()
local integer pzK=GetHandleId(pzT)
local real pzX=GetUnitX(pzU)
local real pzY=GetUnitY(pzU)
local real pzA=Atan2(pzTY-pzY,pzTX-pzX)
local integer pzL=GetUnitAbilityLevel(pzU,'AZ10')
local unit pzSp=CreateUnit(GetOwningPlayer(pzU),'eZ04',pzX,pzY,pzA*bj_RADTODEG)
call SaveUnitHandle(PZH,pzK,0,pzU)
call SaveUnitHandle(PZH,pzK,1,pzSp)
call SaveReal(PZH,pzK,2,42.*Cos(pzA))
call SaveReal(PZH,pzK,3,42.*Sin(pzA))
call SaveReal(PZH,pzK,4,0.)
call SaveReal(PZH,pzK,5,800.+100.*pzL)
call SaveInteger(PZH,pzK,7,pzL)
call SaveGroupHandle(PZH,pzK,9,CreateGroup())
call TimerStart(pzT,0.03,true,function PZSpearTick)
set pzT=null
set pzSp=null
endfunction
// ---------------- Mars: God's Rebuke
function PZRebuke takes unit pzU,real pzTX,real pzTY returns nothing
local real pzX=GetUnitX(pzU)
local real pzY=GetUnitY(pzU)
local real pzA=Atan2(pzTY-pzY,pzTX-pzX)
local integer pzL=GetUnitAbilityLevel(pzU,'AZ11')
local real pzDmg=PZAtk(pzU)*(1.1+0.4*pzL)
local real pzB
local real pzD
local unit pzT
call SetUnitFacing(pzU,pzA*bj_RADTODEG)
call PZFx("H\\Mars\\GodsRebukeAoEFX.mdx",pzX+200.*Cos(pzA),pzY+200.*Sin(pzA),0.)
call GroupEnumUnitsInRange(PZG1,pzX,pzY,550.,null)
loop
set pzT=FirstOfGroup(PZG1)
exitwhen pzT==null
call GroupRemoveUnit(PZG1,pzT)
if PZIsFoe(pzU,pzT) then
set pzB=Atan2(GetUnitY(pzT)-pzY,GetUnitX(pzT)-pzX)
set pzD=RAbsBJ(pzB-pzA)*bj_RADTODEG
if pzD>180. then
set pzD=360.-pzD
endif
if pzD<=65. then
if IsUnitType(pzT,UNIT_TYPE_HERO) then
call PZDmgPhys(pzU,pzT,pzDmg+25.)
else
call PZDmgPhys(pzU,pzT,pzDmg)
endif
call PZSlow(pzU,pzT,9)
call PZKnock(pzT,pzB,150.,0.25)
endif
endif
endloop
endfunction
// ---------------- Mars: Bulwark
function PZBulwarkFix takes nothing returns nothing
local timer pzT=GetExpiredTimer()
local integer pzK=GetHandleId(pzT)
local unit pzU=LoadUnitHandle(PZH,pzK,0)
call UnitRemoveAbility(pzU,'AZ16')
if PZAlive(pzU) then
call SetWidgetLife(pzU,LoadReal(PZH,pzK,1))
endif
call FlushChildHashtable(PZH,pzK)
call DestroyTimer(pzT)
set pzT=null
set pzU=null
endfunction
function PZBulwarkHit takes nothing returns boolean
local unit pzU=GetTriggerUnit()
local unit pzS=GetEventDamageSource()
local real pzA=GetEventDamage()
local integer pzL=GetUnitAbilityLevel(pzU,'AZ12')
local real pzD
local real pzP=0.
local real pzLife
local real pzWant
local timer pzT
if pzL>0 and pzA>1. and pzS!=null and pzS!=pzU and GetUnitCurrentOrder(pzS)==851983 then
set pzD=RAbsBJ(GetUnitFacing(pzU)-Atan2(GetUnitY(pzS)-GetUnitY(pzU),GetUnitX(pzS)-GetUnitX(pzU))*bj_RADTODEG)
loop
exitwhen pzD<=360.
set pzD=pzD-360.
endloop
if pzD>180. then
set pzD=360.-pzD
endif
if pzD<=70. then
set pzP=0.3+0.1*pzL
elseif pzD<=115. then
set pzP=0.15+0.05*pzL
endif
set pzLife=GetWidgetLife(pzU)
set pzWant=pzLife-pzA*(1.-pzP)
if pzP>0. and pzWant>0.405 then
if pzLife+pzA*pzP>GetUnitState(pzU,UNIT_STATE_MAX_LIFE)-1. then
call UnitAddAbility(pzU,'AZ16')
endif
call SetWidgetLife(pzU,pzLife+pzA*pzP)
call PZCount(pzU,51)
set pzT=CreateTimer()
call SaveUnitHandle(PZH,GetHandleId(pzT),0,pzU)
call SaveReal(PZH,GetHandleId(pzT),1,pzWant)
call TimerStart(pzT,0.,false,function PZBulwarkFix)
endif
endif
set pzU=null
set pzS=null
set pzT=null
return false
endfunction
// ---------------- Mars: Arena of Blood
function PZArenaEnd takes timer pzT returns nothing
local integer pzK=GetHandleId(pzT)
local group pzG=LoadGroupHandle(PZH,pzK,5)
local unit pzS
loop
set pzS=FirstOfGroup(pzG)
exitwhen pzS==null
call GroupRemoveUnit(pzG,pzS)
call RemoveUnit(pzS)
endloop
call DestroyGroup(pzG)
call FlushChildHashtable(PZH,pzK)
call DestroyTimer(pzT)
set pzG=null
endfunction
function PZArenaTick takes nothing returns nothing
local timer pzT=GetExpiredTimer()
local integer pzK=GetHandleId(pzT)
local unit pzU=LoadUnitHandle(PZH,pzK,0)
local real pzCX=LoadReal(PZH,pzK,1)
local real pzCY=LoadReal(PZH,pzK,2)
local integer pzL=LoadInteger(PZH,pzK,4)
local real pzNow=PZNow()
local unit pzV
local integer pzVK
local integer pzSt
local real pzDX
local real pzDY
local real pzD
local real pzA
if pzNow>=LoadReal(PZH,pzK,3) then
call PZArenaEnd(pzT)
set pzT=null
set pzU=null
return
endif
call GroupEnumUnitsInRange(PZG2,pzCX,pzCY,700.,null)
loop
set pzV=FirstOfGroup(PZG2)
exitwhen pzV==null
call GroupRemoveUnit(PZG2,pzV)
if PZIsFoe(pzU,pzV) and not IsUnitType(pzV,UNIT_TYPE_FLYING) and not IsUnitType(pzV,UNIT_TYPE_MAGIC_IMMUNE) then
set pzVK=GetHandleId(pzV)
set pzDX=GetUnitX(pzV)-pzCX
set pzDY=GetUnitY(pzV)-pzCY
set pzD=SquareRoot(pzDX*pzDX+pzDY*pzDY)
set pzA=Atan2(pzDY,pzDX)
set pzSt=LoadInteger(PZH,pzK,pzVK)
if pzSt==0 then
if pzD<550. then
set pzSt=1
else
set pzSt=2
endif
call SaveInteger(PZH,pzK,pzVK,pzSt)
endif
if pzSt==1 and pzD>510. then
call SetUnitX(pzV,PZCX(pzCX+500.*Cos(pzA)))
call SetUnitY(pzV,PZCY(pzCY+500.*Sin(pzA)))
elseif pzSt==2 and pzD<590. then
call SetUnitX(pzV,PZCX(pzCX+600.*Cos(pzA)))
call SetUnitY(pzV,PZCY(pzCY+600.*Sin(pzA)))
endif
if pzSt==1 and pzD>390. and IsUnitType(pzV,UNIT_TYPE_HERO) and pzNow>=LoadReal(PZH,pzK,-pzVK) then
call SaveReal(PZH,pzK,-pzVK,pzNow+1.)
call PZDmgMagic(pzU,pzV,55.+65.*pzL)
call PZCount(pzU,55)
call PZFx("H\\Mars\\PushbackSpearsNew.mdx",GetUnitX(pzV),GetUnitY(pzV),0.)
call PZKnock(pzV,pzA+bj_PI,200.,0.2)
endif
endif
endloop
set pzT=null
set pzU=null
set pzV=null
endfunction
function PZArena takes unit pzU,real pzCX,real pzCY returns nothing
local timer pzT=CreateTimer()
local integer pzK=GetHandleId(pzT)
local group pzG=CreateGroup()
local integer pzL=GetUnitAbilityLevel(pzU,'AZ13')
local integer pzI=0
local real pzA
local unit pzS
call SaveUnitHandle(PZH,pzK,0,pzU)
call SaveReal(PZH,pzK,1,pzCX)
call SaveReal(PZH,pzK,2,pzCY)
call SaveReal(PZH,pzK,3,PZNow()+4.1+pzL)
call SaveInteger(PZH,pzK,4,pzL)
call SaveGroupHandle(PZH,pzK,5,pzG)
loop
exitwhen pzI>=24
set pzA=pzI*15.*bj_DEGTORAD
set pzS=CreateUnit(GetOwningPlayer(pzU),'eZ03',PZCX(pzCX+550.*Cos(pzA)),PZCY(pzCY+550.*Sin(pzA)),pzA*bj_RADTODEG+180.)
call GroupAddUnit(pzG,pzS)
set pzI=pzI+1
endloop
call TimerStart(pzT,0.03,true,function PZArenaTick)
set pzT=null
set pzG=null
set pzS=null
endfunction
// ---------------- events
function PZOnSpell takes nothing returns boolean
local unit pzU=GetTriggerUnit()
local integer pzA=GetSpellAbilityId()
local eventid pzE=GetTriggerEventId()
if pzE==EVENT_PLAYER_UNIT_SPELL_EFFECT then
if pzA=='AZ02' or pzA=='AZ04' or pzA=='AZ08' or pzA=='AZ10' or pzA=='AZ11' or pzA=='AZ13' then
call SaveReal(PZH,GetHandleId(pzU),pzA,PZNow()+PZCooldown(pzA,GetUnitAbilityLevel(pzU,pzA)))
endif
if pzA=='AZ02' or pzA=='AZ03' or pzA=='AZ04' or pzA=='AZ08' or pzA=='AZ10' or pzA=='AZ11' or pzA=='AZ13' then
call PZCount(pzU,50)
call PZLog(GetUnitName(pzU)+" (P"+I2S(GetPlayerId(GetOwningPlayer(pzU)))+") casts "+GetObjectName(pzA)+" lvl "+I2S(GetUnitAbilityLevel(pzU,pzA)))
endif
if pzA=='AZ02' then
call PZBoundless(pzU,GetSpellTargetX(),GetSpellTargetY())
elseif pzA=='AZ03' then
call PZTreeDance(pzU,GetSpellTargetX(),GetSpellTargetY())
elseif pzA=='AZ08' then
call PZWukong(pzU,GetSpellTargetX(),GetSpellTargetY())
elseif pzA=='AZ10' then
call PZSpear(pzU,GetSpellTargetX(),GetSpellTargetY())
elseif pzA=='AZ11' then
call PZRebuke(pzU,GetSpellTargetX(),GetSpellTargetY())
elseif pzA=='AZ13' then
call PZArena(pzU,GetSpellTargetX(),GetSpellTargetY())
endif
elseif pzE==EVENT_PLAYER_UNIT_SPELL_CHANNEL then
if pzA=='AZ04' then
call PZSpringStart(pzU,GetSpellTargetX(),GetSpellTargetY())
endif
elseif pzE==EVENT_PLAYER_UNIT_SPELL_ENDCAST then
if pzA=='AZ04' then
call PZSpringEnd(pzU)
endif
endif
set pzU=null
set pzE=null
return false
endfunction
function PZOnAttack takes nothing returns boolean
local unit pzU=GetAttacker()
if GetUnitAbilityLevel(pzU,'AZ05')>0 and not IsUnitIllusion(pzU) then
call PZJinguAttack(pzU,GetTriggerUnit())
endif
set pzU=null
return false
endfunction
function PZOnOrder takes nothing returns boolean
local unit pzU=GetTriggerUnit()
local integer pzO=GetIssuedOrderId()
local integer pzK=GetHandleId(pzU)
if GetUnitTypeId(pzU)=='H0MK' and LoadBoolean(PZH,pzK,10) and not LoadBoolean(PZH,pzK,14) then
if pzO==851986 or pzO==851971 or pzO==851983 or pzO==851990 then
call PZUnperch(pzU)
endif
endif
set pzU=null
return false
endfunction
function PZOnLearn takes nothing returns boolean
local unit pzU=GetTriggerUnit()
local integer pzL
if GetLearnedSkill()=='AZ03' then
set pzL=GetUnitAbilityLevel(pzU,'AZ03')
if GetUnitAbilityLevel(pzU,'AZ04')==0 then
call UnitAddAbility(pzU,'AZ04')
call UnitMakeAbilityPermanent(pzU,true,'AZ04')
endif
call SetUnitAbilityLevel(pzU,'AZ04',pzL)
call PZSetSpringAvail(pzU,LoadBoolean(PZH,GetHandleId(pzU),10))
endif
set pzU=null
return false
endfunction
function PZRegister takes unit pzU returns nothing
local integer pzK=GetHandleId(pzU)
if LoadBoolean(PZH,pzK,1) then
return
endif
call SaveBoolean(PZH,pzK,1,true)
if UnitAddAbility(pzU,'Amrf') then
call UnitRemoveAbility(pzU,'Amrf')
endif
if not IsUnitIllusion(pzU) then
call GroupAddUnit(PZHeroes,pzU)
endif
if GetUnitTypeId(pzU)=='HMRS' then
call TriggerRegisterUnitEvent(PZBulwarkTrig,pzU,EVENT_UNIT_DAMAGED)
endif
endfunction
function PZOnEnter takes nothing returns boolean
local integer pzI=GetUnitTypeId(GetTriggerUnit())
if pzI=='H0MK' or pzI=='HMRS' then
call PZRegister(GetTriggerUnit())
endif
return false
endfunction
// ---------------- periodic: perch watch, Jingu expiry
function PZWatchOne takes nothing returns nothing
local unit pzU=GetEnumUnit()
local integer pzK=GetHandleId(pzU)
local destructable pzD
if LoadBoolean(PZH,pzK,10) and not LoadBoolean(PZH,pzK,14) then
set pzD=LoadDestructableHandle(PZH,pzK,11)
if not PZAlive(pzU) then
call PZUnperch(pzU)
elseif pzD==null or GetDestructableLife(pzD)<=0.405 then
call PZUnperch(pzU)
call PZStunBy(Player(PLAYER_NEUTRAL_AGGRESSIVE),pzU,4.)
else
call SetUnitX(pzU,LoadReal(PZH,pzK,12))
call SetUnitY(pzU,LoadReal(PZH,pzK,13))
call SetUnitFlyHeight(pzU,220.,0.)
endif
endif
if LoadInteger(PZH,pzK,30)>0 and PZNow()>=LoadReal(PZH,pzK,31) then
call PZJinguOff(pzU)
elseif LoadInteger(PZH,pzK,30)==0 and GetUnitAbilityLevel(pzU,'AZ07')>0 and PZNow()>=LoadReal(PZH,pzK,31) then
call PZJinguOff(pzU)
endif
set pzU=null
set pzD=null
endfunction
function PZWatch takes nothing returns nothing
call ForGroup(PZHeroes,function PZWatchOne)
endfunction
// ---------------- AI casting for computer-controlled Monkey King / Mars
function PZCanCast takes unit pzU,integer pzA,real pzMana returns boolean
return GetUnitAbilityLevel(pzU,pzA)>0 and PZNow()>=PZReadyAt(pzU,pzA) and GetUnitState(pzU,UNIT_STATE_MANA)>=pzMana
endfunction
function PZBusy takes unit pzU returns boolean
local integer pzO=GetUnitCurrentOrder(pzU)
return pzO==OrderId("avengerform") or pzO==OrderId("auravampiric") or pzO==OrderId("autodispel") or pzO==OrderId("ancestralspirittarget") or pzO==OrderId("shockwave") or pzO==OrderId("blizzard") or pzO==OrderId("breathoffire") or LoadBoolean(PZH,GetHandleId(pzU),14)
endfunction
function PZAIOne takes nothing returns nothing
local unit pzU=GetEnumUnit()
local unit pzT
local unit pzBest=null
local real pzBD=1000000000.
local real pzD
local integer pzNear=0
local integer pzTy=GetUnitTypeId(pzU)
local real pzEX
local real pzEY
local destructable pzTree=null
if GetPlayerController(GetOwningPlayer(pzU))!=MAP_CONTROL_COMPUTER or not PZAlive(pzU) or IsUnitPaused(pzU) or PZBusy(pzU) then
set pzU=null
return
endif
call GroupEnumUnitsInRange(PZG3,GetUnitX(pzU),GetUnitY(pzU),1050.,null)
loop
set pzT=FirstOfGroup(PZG3)
exitwhen pzT==null
call GroupRemoveUnit(PZG3,pzT)
if PZIsFoeHero(pzU,pzT) and not IsUnitIllusion(pzT) then
set pzD=SquareRoot((GetUnitX(pzT)-GetUnitX(pzU))*(GetUnitX(pzT)-GetUnitX(pzU))+(GetUnitY(pzT)-GetUnitY(pzU))*(GetUnitY(pzT)-GetUnitY(pzU)))
if pzD<600. then
set pzNear=pzNear+1
endif
if pzD<pzBD then
set pzBD=pzD
set pzBest=pzT
endif
endif
endloop
if pzBest==null then
set pzU=null
return
endif
// low health with an enemy hero close: only use escape spells, the map AI handles the retreat itself
if GetUnitLifePercent(pzU)<35. and pzBD<700. then
if pzTy=='H0MK' and GetUnitAbilityLevel(pzU,'AZ03')>0 and not LoadBoolean(PZH,GetHandleId(pzU),10) and pzBD>1. then
set pzEX=GetUnitX(pzU)+(GetUnitX(pzU)-GetUnitX(pzBest))/pzBD*700.
set pzEY=GetUnitY(pzU)+(GetUnitY(pzU)-GetUnitY(pzBest))/pzBD*700.
set pzTree=PZNearestTree(pzEX,pzEY,450.)
if pzTree!=null then
call IssuePointOrder(pzU,"auravampiric",GetDestructableX(pzTree),GetDestructableY(pzTree))
call PZLog(GetUnitName(pzU)+" escapes with Tree Dance at "+I2S(R2I(GetUnitLifePercent(pzU)))+"% hp")
endif
elseif pzTy=='HMRS' and not IsUnitType(pzBest,UNIT_TYPE_MAGIC_IMMUNE) and PZCanCast(pzU,'AZ10',100.) then
call IssuePointOrder(pzU,"shockwave",GetUnitX(pzBest),GetUnitY(pzBest))
call PZLog(GetUnitName(pzU)+" pushes a chaser away with Spear at "+I2S(R2I(GetUnitLifePercent(pzU)))+"% hp")
endif
set pzU=null
set pzT=null
set pzBest=null
set pzTree=null
return
endif
if pzTy=='H0MK' then
if pzBD<500. and GetUnitLifePercent(pzU)>30. and PZCanCast(pzU,'AZ08',100.) then
call IssuePointOrder(pzU,"ancestralspirittarget",GetUnitX(pzBest),GetUnitY(pzBest))
elseif pzBD<1000. and not IsUnitType(pzBest,UNIT_TYPE_MAGIC_IMMUNE) and PZCanCast(pzU,'AZ02',100.) then
call IssuePointOrder(pzU,"avengerform",GetUnitX(pzBest),GetUnitY(pzBest))
endif
elseif pzTy=='HMRS' then
if pzBD<450. and GetUnitLifePercent(pzU)>25. and (pzNear>=2 or GetUnitLifePercent(pzBest)<70.) and PZCanCast(pzU,'AZ13',200.) then
call IssuePointOrder(pzU,"breathoffire",GetUnitX(pzBest),GetUnitY(pzBest))
elseif pzBD<1000. and not IsUnitType(pzBest,UNIT_TYPE_MAGIC_IMMUNE) and PZCanCast(pzU,'AZ10',100.) then
call IssuePointOrder(pzU,"shockwave",GetUnitX(pzBest),GetUnitY(pzBest))
elseif pzBD<450. and PZCanCast(pzU,'AZ11',80.) then
call IssuePointOrder(pzU,"blizzard",GetUnitX(pzBest),GetUnitY(pzBest))
endif
endif
set pzU=null
set pzT=null
set pzBest=null
endfunction
function PZAI takes nothing returns nothing
call ForGroup(PZHeroes,function PZAIOne)
endfunction
// ---------------- health awareness for every computer hero: retreat earlier when outnumbered
function PZThreatTick takes nothing returns nothing
local integer pzP=1
local unit pzU
local unit pzT
local integer pzE
local integer pzA
local real pzX
local real pzY
loop
exitwhen pzP>11
set PZThreat[pzP]=0.
set pzU=M7[pzP]
if pzP!=6 and pzU!=null and GetPlayerController(Player(pzP))==MAP_CONTROL_COMPUTER and PZAlive(pzU) then
set pzE=0
set pzA=0
set pzX=GetUnitX(pzU)
set pzY=GetUnitY(pzU)
call GroupEnumUnitsInRange(PZG5,pzX,pzY,1000.,null)
loop
set pzT=FirstOfGroup(PZG5)
exitwhen pzT==null
call GroupRemoveUnit(PZG5,pzT)
if pzT!=pzU and IsUnitType(pzT,UNIT_TYPE_HERO) and not IsUnitIllusion(pzT) and PZAlive(pzT) then
if IsUnitEnemy(pzT,Player(pzP)) then
if IsUnitVisible(pzT,Player(pzP)) then
set pzE=pzE+1
endif
else
set pzA=pzA+1
endif
endif
endloop
if pzE>pzA+1 then
set PZThreat[pzP]=RMinBJ(12.*(pzE-pzA-1),30.)
endif
endif
set pzP=pzP+1
endloop
set pzU=null
set pzT=null
endfunction
function PZSumOne takes nothing returns nothing
local unit pzU=GetEnumUnit()
local integer pzK=GetHandleId(pzU)
local string pzC="H"
local string pzL
if GetPlayerController(GetOwningPlayer(pzU))==MAP_CONTROL_COMPUTER then
set pzC="AI"
endif
if GetUnitTypeId(pzU)=='H0MK' then
set pzL=I2S(GetUnitAbilityLevel(pzU,'AZ02'))+"/"+I2S(GetUnitAbilityLevel(pzU,'AZ03'))+"/"+I2S(GetUnitAbilityLevel(pzU,'AZ05'))+"/"+I2S(GetUnitAbilityLevel(pzU,'AZ08'))
else
set pzL=I2S(GetUnitAbilityLevel(pzU,'AZ10'))+"/"+I2S(GetUnitAbilityLevel(pzU,'AZ11'))+"/"+I2S(GetUnitAbilityLevel(pzU,'AZ12'))+"/"+I2S(GetUnitAbilityLevel(pzU,'AZ13'))
endif
call PZLog(GetUnitName(pzU)+" P"+I2S(GetPlayerId(GetOwningPlayer(pzU)))+" "+pzC+" L"+I2S(GetHeroLevel(pzU))+" skills "+pzL+" hp "+I2S(R2I(GetUnitLifePercent(pzU)))+"% casts "+I2S(LoadInteger(PZH,pzK,50))+" bulwark "+I2S(LoadInteger(PZH,pzK,51))+" jingu "+I2S(LoadInteger(PZH,pzK,52))+" pins "+I2S(LoadInteger(PZH,pzK,53))+" soldier hits "+I2S(LoadInteger(PZH,pzK,54))+" arena hits "+I2S(LoadInteger(PZH,pzK,55)))
set pzU=null
endfunction
function PZSummary takes nothing returns nothing
local integer pzP=1
local string pzS=""
call ForGroup(PZHeroes,function PZSumOne)
loop
exitwhen pzP>11
if pzP!=6 and M7[pzP]!=null and GetPlayerSlotState(Player(pzP))==PLAYER_SLOT_STATE_PLAYING then
set pzS=pzS+" P"+I2S(pzP)+":L"+I2S(GetHeroLevel(M7[pzP]))+"/"+I2S(R2I(GetPlayerHandicapXPBJ(Player(pzP))))+"%xp/+"+I2S(Y74[48+pzP])+"g/"+I2S(GetPlayerState(Player(pzP),PLAYER_STATE_RESOURCE_GOLD))+"/t"+I2S(R2I(PZThreat[pzP]))
endif
set pzP=pzP+1
endloop
call PZLog("econ"+pzS)
endfunction
// ---------------- debug-only self test (test build, chat "-pztest")
function PZTLearn takes unit pzU,integer pzA,integer pzN returns nothing
local integer pzI=0
loop
exitwhen pzI>=pzN
call SelectHeroSkill(pzU,pzA)
set pzI=pzI+1
endloop
endfunction
function PZTHp takes unit pzU returns string
return I2S(R2I(GetWidgetLife(pzU)))
endfunction
function PZTCast takes unit pzU,string pzO,real pzX,real pzY returns boolean
local integer pzN=LoadInteger(PZH,GetHandleId(pzU),50)
local integer pzI=0
loop
exitwhen pzI>=6
call SetUnitState(pzU,UNIT_STATE_MANA,9999.)
call IssuePointOrder(pzU,pzO,pzX,pzY)
call TriggerSleepAction(0.8)
if LoadInteger(PZH,GetHandleId(pzU),50)>pzN then
return true
endif
set pzI=pzI+1
endloop
call PZLog("selftest: "+pzO+" was never cast")
return false
endfunction
function PZTDist takes unit pzU,real pzX,real pzY returns string
return I2S(R2I(SquareRoot((GetUnitX(pzU)-pzX)*(GetUnitX(pzU)-pzX)+(GetUnitY(pzU)-pzY)*(GetUnitY(pzU)-pzY))))
endfunction
function PZSelfTest takes nothing returns nothing
local player pzP=GetTriggerPlayer()
local player pzE=Player(7)
local real pzSX=GetStartLocationX(GetPlayerStartLocation(pzP))
local real pzSY=GetStartLocationY(GetPlayerStartLocation(pzP))
local destructable pzD=PZNearestTree(pzSX,pzSY,2500.)
local real pzTX
local real pzTY
local real pzA
local real pzC
local real pzS
local unit pzM
local unit pzR
local unit pzV
local unit pzV2
local unit pzCr
local integer pzI
local real pzH
local boolean pzB
local real pzX0
local real pzY0
if pzD==null then
call PZLog("selftest: no tree found near start")
return
endif
set pzTX=GetDestructableX(pzD)
set pzTY=GetDestructableY(pzD)
set pzA=Atan2(pzSY-pzTY,pzSX-pzTX)
set pzC=Cos(pzA)
set pzS=Sin(pzA)
call PZLog("selftest: tree at "+I2S(R2I(pzTX))+","+I2S(R2I(pzTY)))
call PanCameraToTimed(pzTX+pzC*400.,pzTY+pzS*400.,0.)
// ---- Monkey King
if StringCase(GetEventPlayerChatString(),false)=="-pztest" then
set pzM=CreateUnit(pzP,'H0MK',pzTX+pzC*450.,pzTY+pzS*450.,0.)
call SetHeroLevel(pzM,16,false)
call PZTLearn(pzM,'AZ02',4)
call PZTLearn(pzM,'AZ03',4)
call PZTLearn(pzM,'AZ05',4)
call PZTLearn(pzM,'AZ08',3)
call PZLog("MK created, skills "+I2S(GetUnitAbilityLevel(pzM,'AZ02'))+"/"+I2S(GetUnitAbilityLevel(pzM,'AZ03'))+"/"+I2S(GetUnitAbilityLevel(pzM,'AZ05'))+"/"+I2S(GetUnitAbilityLevel(pzM,'AZ08'))+" spring "+I2S(GetUnitAbilityLevel(pzM,'AZ04')))
call TriggerSleepAction(2.)
call SetUnitPosition(pzM,pzTX+pzC*450.,pzTY+pzS*450.)
call PZLog("MK at dist to tree "+I2S(R2I(SquareRoot((GetUnitX(pzM)-pzTX)*(GetUnitX(pzM)-pzTX)+(GetUnitY(pzM)-pzTY)*(GetUnitY(pzM)-pzTY)))))
call TriggerSleepAction(1.)
call IssuePointOrder(pzM,"auravampiric",pzTX,pzTY)
call TriggerSleepAction(2.)
call PZLog("Tree Dance: perched="+I2S(IntegerTertiaryOp(LoadBoolean(PZH,GetHandleId(pzM),10),1,0))+" flyheight="+I2S(R2I(GetUnitFlyHeight(pzM))))
set pzV=CreateUnit(pzE,'Hvwd',pzTX+pzC*700.,pzTY+pzS*700.,0.)
set pzCr=CreateUnit(pzE,'Hvwd',pzTX+pzC*760.,pzTY+pzS*640.,0.)
call SetHeroLevel(pzV,16,false)
call SetHeroLevel(pzCr,16,false)
call TriggerSleepAction(2.)
call SetUnitPosition(pzV,pzTX+pzC*700.,pzTY+pzS*700.)
call SetUnitPosition(pzCr,pzTX+pzC*760.+pzS*120.,pzTY+pzS*760.-pzC*120.)
call PauseUnit(pzV,true)
call PauseUnit(pzCr,true)
call SetUnitState(pzM,UNIT_STATE_MANA,9999.)
set pzH=GetWidgetLife(pzV)
call IssuePointOrder(pzM,"autodispel",GetUnitX(pzV),GetUnitY(pzV))
call TriggerSleepAction(3.5)
call PZLog("Primal Spring: perched="+I2S(IntegerTertiaryOp(LoadBoolean(PZH,GetHandleId(pzM),10),1,0))+" fly="+I2S(R2I(GetUnitFlyHeight(pzM)))+" target hp "+I2S(R2I(pzH))+" -> "+PZTHp(pzV))
call SetUnitState(pzM,UNIT_STATE_MANA,9999.)
set pzH=GetWidgetLife(pzCr)
call IssuePointOrder(pzM,"avengerform",GetUnitX(pzCr),GetUnitY(pzCr))
call TriggerSleepAction(1.)
call PZLog("Boundless Strike: hp "+I2S(R2I(pzH))+" -> "+PZTHp(pzCr)+" stunned order="+I2S(GetUnitCurrentOrder(pzCr)))
call PauseUnit(pzV,false)
call IssueTargetOrder(pzM,"attack",pzV)
call TriggerSleepAction(7.)
call PZLog("Jingu: charges="+I2S(LoadInteger(PZH,GetHandleId(pzM),30))+" lifesteal lvl="+I2S(GetUnitAbilityLevel(pzM,'AZ06'))+" procs="+I2S(LoadInteger(PZH,GetHandleId(pzM),52)))
call SetUnitState(pzM,UNIT_STATE_MANA,9999.)
call IssuePointOrder(pzM,"ancestralspirittarget",GetUnitX(pzV),GetUnitY(pzV))
call TriggerSleepAction(4.)
call PZLog("Wukong: soldier hits="+I2S(LoadInteger(PZH,GetHandleId(pzM),54))+" armor bonus lvl="+I2S(GetUnitAbilityLevel(pzM,'AZ09')))
call TriggerSleepAction(1.)
call RemoveUnit(pzV)
call RemoveUnit(pzCr)
call RemoveUnit(pzM)
endif
// ---- Mars
set pzR=CreateUnit(pzP,'HMRS',pzTX+pzC*800.,pzTY+pzS*800.,pzA*bj_RADTODEG+180.)
call SetHeroLevel(pzR,16,false)
call PZTLearn(pzR,'AZ10',4)
call PZTLearn(pzR,'AZ11',4)
call PZTLearn(pzR,'AZ12',4)
call PZTLearn(pzR,'AZ13',3)
call PZLog("Mars created, skills "+I2S(GetUnitAbilityLevel(pzR,'AZ10'))+"/"+I2S(GetUnitAbilityLevel(pzR,'AZ11'))+"/"+I2S(GetUnitAbilityLevel(pzR,'AZ12'))+"/"+I2S(GetUnitAbilityLevel(pzR,'AZ13')))
set pzV=CreateUnit(pzE,'Hvwd',pzTX+pzC*300.,pzTY+pzS*300.,0.)
call SetHeroLevel(pzV,16,false)
call TriggerSleepAction(2.)
call SetUnitPosition(pzR,pzTX+pzC*800.,pzTY+pzS*800.)
call SetUnitPosition(pzV,pzTX+pzC*300.,pzTY+pzS*300.)
call PauseUnit(pzV,true)
call IssueImmediateOrder(pzR,"stop")
call PanCameraToTimed(pzTX+pzC*500.,pzTY+pzS*500.,0.)
set pzH=GetWidgetLife(pzV)
set pzB=PZTCast(pzR,"shockwave",pzTX,pzTY)
call TriggerSleepAction(1.5)
call PZLog("Spear: cast="+I2S(IntegerTertiaryOp(pzB,1,0))+" hp "+I2S(R2I(pzH))+" -> "+PZTHp(pzV)+" pins="+I2S(LoadInteger(PZH,GetHandleId(pzR),53))+" target dist to tree="+PZTDist(pzV,pzTX,pzTY)+" stunned="+I2S(IntegerTertiaryOp(GetUnitCurrentOrder(pzV)==851973,1,0)))
call PauseUnit(pzV,false)
call TriggerSleepAction(3.)
call SetUnitPosition(pzV,GetUnitX(pzR)-pzC*250.,GetUnitY(pzR)-pzS*250.)
call PauseUnit(pzV,true)
set pzH=GetWidgetLife(pzV)
set pzB=PZTCast(pzR,"blizzard",GetUnitX(pzV),GetUnitY(pzV))
call TriggerSleepAction(0.3)
call PZLog("Rebuke: cast="+I2S(IntegerTertiaryOp(pzB,1,0))+" hp "+I2S(R2I(pzH))+" -> "+PZTHp(pzV)+" slowed="+I2S(GetUnitAbilityLevel(pzV,'Bslo'))+" pushed to "+PZTDist(pzV,GetUnitX(pzR),GetUnitY(pzR)))
call PauseUnit(pzV,false)
set pzX0=GetUnitX(pzR)
set pzY0=GetUnitY(pzR)
call SetUnitPosition(pzV,pzX0-pzC*470.,pzY0-pzS*470.)
call PauseUnit(pzV,true)
set pzB=PZTCast(pzR,"breathoffire",pzX0,pzY0)
call PauseUnit(pzV,false)
call IssuePointOrder(pzV,"move",pzX0-pzC*1200.,pzY0-pzS*1200.)
call TriggerSleepAction(3.)
call PZLog("Arena: cast="+I2S(IntegerTertiaryOp(pzB,1,0))+" spear hits="+I2S(LoadInteger(PZH,GetHandleId(pzR),55))+" enemy tried to walk out, dist from center="+PZTDist(pzV,pzX0,pzY0))
set pzI=0
loop
exitwhen pzI>=3
set pzV2=CreateUnit(pzE,'Hvwd',GetUnitX(pzR)-pzC*300.,GetUnitY(pzR)-pzS*300.,0.)
call SaveUnitHandle(PZH,GetHandleId(pzR),60+pzI,pzV2)
set pzI=pzI+1
endloop
call TriggerSleepAction(2.)
set pzI=0
loop
exitwhen pzI>=3
set pzV2=LoadUnitHandle(PZH,GetHandleId(pzR),60+pzI)
call SetUnitPosition(pzV2,GetUnitX(pzR)-pzC*250.+pzS*(pzI-1)*80.,GetUnitY(pzR)-pzS*250.-pzC*(pzI-1)*80.)
call IssueTargetOrder(pzV2,"attack",pzR)
set pzI=pzI+1
endloop
call IssueImmediateOrder(pzR,"stop")
call SetUnitFacing(pzR,pzA*bj_RADTODEG+180.)
call PauseUnit(pzR,true)
call TriggerSleepAction(5.)
call PauseUnit(pzR,false)
call PZLog("Bulwark: blocked hits="+I2S(LoadInteger(PZH,GetHandleId(pzR),51))+" mars hp "+PZTHp(pzR))
call PZLog("selftest done")
set pzP=null
set pzE=null
set pzD=null
set pzM=null
set pzR=null
set pzV=null
set pzV2=null
set pzCr=null
endfunction
function PZLogPlayers takes nothing returns nothing
local integer pzI=0
local string pzS=""
loop
exitwhen pzI>11
if GetPlayerSlotState(Player(pzI))==PLAYER_SLOT_STATE_PLAYING then
if GetPlayerController(Player(pzI))==MAP_CONTROL_COMPUTER then
set pzS=pzS+" "+I2S(pzI)+":AI"
elseif GetPlayerController(Player(pzI))==MAP_CONTROL_USER then
set pzS=pzS+" "+I2S(pzI)+":user"
else
set pzS=pzS+" "+I2S(pzI)+":other"
endif
endif
set pzI=pzI+1
endloop
call PZLog("playing slots:"+pzS)
call DestroyTimer(GetExpiredTimer())
endfunction
// ---------------- hooks used by the patched map code
function PZRandHero takes integer pzLo,integer pzHi returns integer
local integer pzI
if PZPickTest>0 then
set pzI=112+PZPickTest
set PZPickTest=PZPickTest+1
if PZPickTest>2 then
set PZPickTest=1
endif
if not J[pzI] then
return pzI
endif
endif
if GetRandomInt(1,100)<=PZRandChance then
set pzI=GetRandomInt(113,114)
if not J[pzI] then
return pzI
endif
set pzI=227-pzI
if not J[pzI] then
return pzI
endif
endif
return GetRandomInt(pzLo,pzHi)
endfunction
function PZInit takes nothing returns nothing
local trigger pzT
local integer pzI=0
call TimerStart(PZClock,999999.,false,null)
set PZRect=Rect(0.,0.,1.,1.)
set PZMinX=GetRectMinX(bj_mapInitialPlayableArea)+64.
set PZMinY=GetRectMinY(bj_mapInitialPlayableArea)+64.
set PZMaxX=GetRectMaxX(bj_mapInitialPlayableArea)-64.
set PZMaxY=GetRectMaxY(bj_mapInitialPlayableArea)-64.
set PZHarv=CreateUnit(Player(PLAYER_NEUTRAL_PASSIVE),'eZ05',0.,0.,0.)
call ShowUnit(PZHarv,false)
set PZBulwarkTrig=CreateTrigger()
call TriggerAddCondition(PZBulwarkTrig,Condition(function PZBulwarkHit))
set pzT=CreateTrigger()
call TriggerRegisterAnyUnitEventBJ(pzT,EVENT_PLAYER_UNIT_SPELL_EFFECT)
call TriggerRegisterAnyUnitEventBJ(pzT,EVENT_PLAYER_UNIT_SPELL_CHANNEL)
call TriggerRegisterAnyUnitEventBJ(pzT,EVENT_PLAYER_UNIT_SPELL_ENDCAST)
call TriggerAddCondition(pzT,Condition(function PZOnSpell))
set pzT=CreateTrigger()
call TriggerRegisterAnyUnitEventBJ(pzT,EVENT_PLAYER_UNIT_ATTACKED)
call TriggerAddCondition(pzT,Condition(function PZOnAttack))
set pzT=CreateTrigger()
call TriggerRegisterAnyUnitEventBJ(pzT,EVENT_PLAYER_UNIT_ISSUED_POINT_ORDER)
call TriggerRegisterAnyUnitEventBJ(pzT,EVENT_PLAYER_UNIT_ISSUED_TARGET_ORDER)
call TriggerAddCondition(pzT,Condition(function PZOnOrder))
set pzT=CreateTrigger()
call TriggerRegisterAnyUnitEventBJ(pzT,EVENT_PLAYER_HERO_SKILL)
call TriggerAddCondition(pzT,Condition(function PZOnLearn))
set pzT=CreateTrigger()
call TriggerRegisterEnterRectSimple(pzT,GetWorldBounds())
call TriggerAddCondition(pzT,Condition(function PZOnEnter))
call TimerStart(CreateTimer(),0.1,true,function PZWatch)
call TimerStart(CreateTimer(),0.35,true,function PZAI)
call TimerStart(CreateTimer(),0.5,true,function PZThreatTick)
if PZDebug then
call TimerStart(CreateTimer(),30.,true,function PZSummary)
call TimerStart(CreateTimer(),3.,false,function PZLogPlayers)
set pzT=CreateTrigger()
set pzI=0
loop
exitwhen pzI>11
call TriggerRegisterPlayerChatEvent(pzT,Player(pzI),"-pztest",false)
set pzI=pzI+1
endloop
call TriggerAddAction(pzT,function PZSelfTest)
set pzI=0
endif
loop
exitwhen pzI>15
call SetPlayerAbilityAvailable(Player(pzI),'AZ04',false)
set pzI=pzI+1
endloop
set pzT=null
endfunction
