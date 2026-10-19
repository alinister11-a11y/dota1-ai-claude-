//@GLOBALS
// ---- Claude bridge (injected by patch_map.py) ----
player AzCP=null
player AzOwner=null
boolean AzMan=false
boolean AzNoAIPick=false
boolean AzAuto=true
boolean AzLinked=false
boolean AzFallback=false
boolean AzWasPicked=false
real AzHold=0.
real AzHoldLen=8.
real AzTime=0.
real AzLastCmd=-1000.
real AzWait=75.
real AzIdleMax=150.
integer AzNonce=0
integer AzSeq=0
integer AzOwnSeq=-1
gamecache AzGC=null
group AzG=null
group AzGx=null
integer AzHumans=0
string array AzEv
real array AzEvT
integer AzEvN=0
string array AzTk
string array AzCm
string array AzOut
integer AzOutN=0
string AzLB=""
string AzLP=""
string AzCS=" !\"#$%&'()*+,-./0123456789:;<=>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ[\\]^_`abcdefghijklmnopqrstuvwxyz{|}~"
integer array AzAb
real array AzAbT
integer AzAbN=0
integer array AzBld
boolean array AzBldU
integer AzBldN=0
boolean AzBusy=false
string array AzPName
real AzDmg=0.
integer AzDmgBy=-1
trigger AzDmgTrig=null
unit AzDmgHero=null
real AzFx=0.
real AzFy=0.
integer AzOk=0
integer AzErr=0
real AzPtsT=0.
real AzRetreatPct=20.
boolean AzRetreating=false
boolean AzSolo=false
integer AzSoloQ=0
integer array AzCi
integer AzCn=0
real AzExpPeriod=15.
real AzExpAcc=0.
boolean AzExpNow=true
integer AzReqSeen=-1
real AzWatchEnd=0.
integer AzWatchMask=0
real AzWatchDmg=0.
boolean AzWatchLow=false
boolean AzWatchAlive=true
boolean AzWatchHero=false
integer AzWatchPts=0
integer AzWatchImp=0
integer AzImpN=0
boolean array AzWVis
string AzWake=""
real AzPollPeriod=.5
real AzPollAcc=0.
integer AzExpMode=2
integer AzExpN=0
//@CTL
function AzCtl takes player p returns mapcontrol
if AzMan and p==AzCP then
return MAP_CONTROL_USER
endif
return GetPlayerController(p)
endfunction
function AzPInAI takes player p,force f returns boolean
if AzMan and p==AzCP then
return false
endif
return IsPlayerInForce(p,f)
endfunction
function AzUInAI takes unit u,force f returns boolean
if AzMan and GetOwningPlayer(u)==AzCP then
return false
endif
return IsUnitInForce(u,f)
endfunction
//@FUNCS
function AzEvent takes string s returns nothing
local integer i=AzEvN-(AzEvN/24)*24
local string w=SubString(s,0,4)
set AzEv[i]=s
set AzEvT[i]=AzTime
set AzEvN=AzEvN+1
if w=="kill" or w=="chat" or w=="buil" or w=="leve" or w=="info" then
set AzImpN=AzImpN+1
endif
endfunction
function AzSplit takes string s returns integer
local integer i=0
local integer n=0
local integer st=0
local integer slen=StringLength(s)
loop
exitwhen i>slen or n>=60
if i==slen or SubString(s,i,i+1)==" " then
if i>st then
set AzTk[n]=SubString(s,st,i)
set n=n+1
endif
set st=i+1
endif
set i=i+1
endloop
return n
endfunction
function AzSplitCmds takes string s returns integer
local integer i=0
local integer n=0
local integer st=0
local integer slen=StringLength(s)
loop
exitwhen i>slen or n>=20
if i==slen or SubString(s,i,i+1)==";" then
if i>st then
set AzCm[n]=SubString(s,st,i)
set n=n+1
endif
set st=i+1
endif
set i=i+1
endloop
return n
endfunction
function AzHero takes nothing returns unit
if AzCP==null then
return null
endif
return M7[GetPlayerId(AzCP)]
endfunction
function AzScan takes integer k returns unit
local unit u
local unit r=null
loop
set u=FirstOfGroup(AzG)
exitwhen u==null
call GroupRemoveUnit(AzG,u)
if GetHandleId(u)==k then
set r=u
endif
endloop
return r
endfunction
function AzUnitById takes integer k returns unit
local unit h=AzHero()
local unit r=null
if h!=null then
call GroupEnumUnitsInRange(AzG,GetUnitX(h),GetUnitY(h),3000.,null)
set r=AzScan(k)
endif
if r==null then
call GroupEnumUnitsOfPlayer(AzG,Z7[0],null)
set r=AzScan(k)
endif
if r==null then
call GroupEnumUnitsOfPlayer(AzG,A7[0],null)
set r=AzScan(k)
endif
set h=null
return r
endfunction
function AzUnit takes string s returns unit
local integer k
local string c
if StringLength(s)<2 then
return null
endif
set c=SubString(s,0,1)
set k=S2I(SubString(s,1,StringLength(s)))
if c=="h" then
if k>=0 and k<12 then
return M7[k]
endif
return null
elseif c=="u" then
return AzUnitById(k)
endif
return null
endfunction
function AzTouch takes nothing returns nothing
if AzAuto then
set AzHold=AzTime+AzHoldLen
endif
set AzMan=true
endfunction
function AzFindComp takes integer a,integer b returns player
local integer i=a
loop
exitwhen i>b
if i!=6 and GetPlayerSlotState(Player(i))==PLAYER_SLOT_STATE_PLAYING and GetPlayerController(Player(i))==MAP_CONTROL_COMPUTER then
return Player(i)
endif
set i=i+1
endloop
return null
endfunction
function AzHeroIdx takes integer h returns integer
local integer i=0
loop
exitwhen i>K54
if K34[i]==h then
return i
endif
set i=i+1
endloop
return -1
endfunction
function AzPick takes integer h returns string
local integer i=AzHeroIdx(h)
local integer pid=GetPlayerId(AzCP)
local real x
local real y
if M7[pid]!=null then
return "err already have a hero"
endif
if i<0 then
return "err unknown hero"
endif
if J[i] then
return "err hero already taken"
endif
if GetPlayerTechMaxAllowed(AzCP,h)==0 then
return "err hero not allowed in this mode"
endif
if TV7(AzCP) then
set x=GetRandomReal(GetRectMinX(ED),GetRectMaxX(ED))
set y=GetRandomReal(GetRectMinY(ED),GetRectMaxY(ED))
else
set x=GetRandomReal(GetRectMinX(L9),GetRectMaxX(L9))
set y=GetRandomReal(GetRectMinY(L9),GetRectMaxY(L9))
endif
set eY[pid]=0
set M7[pid]=CreateUnit(AzCP,h,x,y,bj_UNIT_FACING)
if M7[pid]==null then
return "err could not create hero"
endif
return "ok picked"
endfunction
function AzFallbackPick takes nothing returns nothing
set AzNoAIPick=false
if AzCP!=null and M7[GetPlayerId(AzCP)]==null then
set AzMan=false
call XZE(GetPlayerId(AzCP),0)
call AzEvent("info Claude did not pick in time: the AI picked a random hero for this slot")
endif
endfunction
function AzCast takes unit h,integer a,string ord,string t1,string t2 returns string
local integer o=OrderId(ord)
local unit t=null
if GetUnitAbilityLevel(h,a)<=0 then
return "err ability not learned"
endif
if o==0 then
return "err unknown order "+ord
endif
if t2!="" then
if IssuePointOrderById(h,o,S2R(t1),S2R(t2)) then
return "ok cast at point"
endif
return "err point cast refused (skill may need a unit target, or is on cooldown / low mana)"
endif
if t1!="" then
set t=AzUnit(t1)
if t==null or GetWidgetLife(t)<.405 then
set t=null
return "err no such living target "+t1
endif
if not IsUnitVisible(t,AzCP) then
set t=null
return "err target is not visible to you"
endif
if IssueTargetOrderById(h,o,t) then
set t=null
return "ok cast on target"
endif
if IssuePointOrderById(h,o,GetUnitX(t),GetUnitY(t)) then
set t=null
return "ok cast at target position"
endif
set t=null
return "err cast refused (cooldown, mana, invalid or magic-immune target)"
endif
if IssueImmediateOrderById(h,o) then
return "ok cast"
endif
if IssueTargetOrderById(h,o,h) then
return "ok cast on self"
endif
return "err cast refused (skill may need a target, or is on cooldown / low mana)"
endfunction
function AzBuy takes unit h,integer tok returns string
local unit u
local boolean okb=false
call GroupEnumUnitsInRange(AzG,GetUnitX(h),GetUnitY(h),1100.,null)
loop
set u=FirstOfGroup(AzG)
exitwhen u==null
call GroupRemoveUnit(AzG,u)
if not okb and u!=h and GetOwningPlayer(u)!=AzCP and not IsUnitType(u,UNIT_TYPE_HERO) then
set okb=IssueNeutralImmediateOrderById(AzCP,u,tok)
endif
endloop
call GroupClear(AzG)
set u=null
if okb then
return "ok buy order sent"
endif
return "err no shop within range sells that now (walk to the shop; it may be out of stock)"
endfunction
function AzUse takes unit h,integer slot,string t1,string t2 returns string
local item it=UnitItemInSlot(h,slot-1)
local unit t
local boolean okb=false
if it==null then
return "err empty slot"
endif
if t2!="" then
set okb=UnitUseItemPoint(h,it,S2R(t1),S2R(t2))
elseif t1!="" then
set t=AzUnit(t1)
if t!=null then
set okb=UnitUseItemTarget(h,it,t)
endif
set t=null
else
set okb=UnitUseItem(h,it)
endif
set it=null
if okb then
return "ok used item"
endif
return "err item use refused"
endfunction
function AzLearnBuild takes unit h returns nothing
local integer i=0
local integer pts=GetHeroSkillPoints(h)
loop
exitwhen i>=AzBldN or pts<=0
if not AzBldU[i] then
call SelectHeroSkill(h,AzBld[i])
if GetHeroSkillPoints(h)<pts then
set AzBldU[i]=true
set pts=GetHeroSkillPoints(h)
endif
endif
set i=i+1
endloop
endfunction
function AzExec1 takes string cmd returns string
local integer n=AzSplit(cmd)
local string opc
local unit h=AzHero()
local unit t
local integer i
local string r="ok"
if n==0 then
return "err empty"
endif
set opc=AzTk[0]
if opc=="hello" or opc=="ping" then
return "ok "+opc
elseif opc=="mode" then
set AzAuto=(AzTk[1]=="auto")
if AzAuto then
set AzHold=0.
endif
return "ok mode "+AzTk[1]
elseif opc=="hold" then
set AzHoldLen=RMaxBJ(1.,RMinBJ(120.,S2R(AzTk[1])))
return "ok hold "+R2SW(AzHoldLen,1,0)
elseif opc=="rt" then
set AzRetreatPct=RMaxBJ(0.,RMinBJ(90.,S2R(AzTk[1])))
return "ok auto-retreat below "+R2SW(AzRetreatPct,1,0)+"%"
elseif opc=="cfg" then
set AzExpPeriod=RMaxBJ(.25,S2R(AzTk[1]))
set AzPollPeriod=RMaxBJ(.1,S2R(AzTk[2]))
set AzExpMode=S2I(AzTk[3])
return "ok cfg"
elseif opc=="say" then
call DisplayTimedTextToPlayer(GetLocalPlayer(),0,0,12.,"|cffff8000[All] Claude:|r "+SubString(cmd,4,StringLength(cmd)))
return "ok said"
elseif opc=="trk" then
set AzAbN=0
loop
exitwhen AzAbN>=n-1 or AzAbN>=8
if AzAb[AzAbN]!=S2I(AzTk[AzAbN+1]) then
set AzAb[AzAbN]=S2I(AzTk[AzAbN+1])
set AzAbT[AzAbN]=-1000.
endif
set AzAbN=AzAbN+1
endloop
return "ok tracking "+I2S(AzAbN)
elseif opc=="build" then
set AzBldN=0
loop
exitwhen AzBldN>=n-1 or AzBldN>=30
set AzBld[AzBldN]=AzAb[S2I(AzTk[AzBldN+1])]
set AzBldU[AzBldN]=false
set AzBldN=AzBldN+1
endloop
return "ok build "+I2S(AzBldN)
elseif opc=="pick" then
return AzPick(S2I(AzTk[1]))
elseif h==null then
return "err no hero yet"
elseif opc=="lr" then
set i=GetHeroSkillPoints(h)
call SelectHeroSkill(h,S2I(AzTk[1]))
if GetHeroSkillPoints(h)<i then
return "ok learned"
endif
return "err cannot learn that now"
endif
if GetWidgetLife(h)<.405 then
return "err hero is dead"
endif
call AzTouch()
if opc=="mv" then
if IssuePointOrderById(h,851986,S2R(AzTk[1]),S2R(AzTk[2])) then
return "ok moving"
endif
return "err move refused"
elseif opc=="am" then
if IssuePointOrderById(h,851983,S2R(AzTk[1]),S2R(AzTk[2])) then
return "ok attack-moving"
endif
return "err attack-move refused"
elseif opc=="at" then
set t=AzUnit(AzTk[1])
if t==null or GetWidgetLife(t)<.405 then
return "err no such living target"
endif
if IssueTargetOrderById(h,851983,t) then
set t=null
return "ok attacking"
endif
set t=null
return "err attack refused"
elseif opc=="st" then
call IssueImmediateOrderById(h,851972)
return "ok stopped"
elseif opc=="hp" then
call IssueImmediateOrderById(h,851993)
return "ok holding position"
elseif opc=="bk" then
call IssuePointOrderById(h,851986,AzFx,AzFy)
return "ok returning to fountain"
elseif opc=="cs" then
if n>=5 then
return AzCast(h,S2I(AzTk[1]),AzTk[2],AzTk[3],AzTk[4])
elseif n==4 then
return AzCast(h,S2I(AzTk[1]),AzTk[2],AzTk[3],"")
endif
return AzCast(h,S2I(AzTk[1]),AzTk[2],"","")
elseif opc=="by" then
return AzBuy(h,S2I(AzTk[1]))
elseif opc=="us" then
if n>=4 then
return AzUse(h,S2I(AzTk[1]),AzTk[2],AzTk[3])
elseif n==3 then
return AzUse(h,S2I(AzTk[1]),AzTk[2],"")
endif
return AzUse(h,S2I(AzTk[1]),"","")
endif
return "err unknown command "+opc
endfunction
function AzRun takes integer q returns nothing
local integer c=AzCn
local integer i=0
local integer j
local integer v
local integer k
local integer m
local string s=""
local string r
loop
exitwhen i>=c
set v=AzCi[i]
set j=0
loop
exitwhen j>3
set k=v-(v/96)*96
set v=v/96
if k>0 then
set s=s+SubString(AzCS,k-1,k)
endif
set j=j+1
endloop
set i=i+1
endloop
set AzLinked=true
set AzLastCmd=AzTime
set m=AzSplitCmds(s)
set i=0
loop
exitwhen i>=m
set r=AzExec1(AzCm[i])
if SubString(r,0,2)=="ok" then
set AzOk=AzOk+1
else
set AzErr=AzErr+1
endif
call AzEvent("res "+I2S(q)+" "+AzTk[0]+" "+r)
set i=i+1
endloop
set AzExpNow=true
endfunction
// ---- watch requests: the server asks "wake me when X", the owner's PC checks each tick without any I/O
// and writes state.txt once when something happens or time runs out. Owner-local; no game state changes.
function AzVisEnemy takes integer pid returns boolean
local unit u=M7[pid]
local boolean b=u!=null and Player(pid)!=AzCP and IsPlayerEnemy(Player(pid),AzCP) and GetWidgetLife(u)>.405 and IsUnitVisible(u,AzCP)
set u=null
return b
endfunction
function AzWatchStart takes integer tenths,integer wmsk returns nothing
local unit h=AzHero()
local integer i=1
set AzWatchEnd=AzTime+I2R(tenths)/10.
set AzWatchMask=wmsk
set AzWatchDmg=0.
set AzWatchImp=AzImpN
set AzWake=""
loop
exitwhen i>11
set AzWVis[i]=AzVisEnemy(i)
set i=i+1
endloop
set AzWatchHero=h!=null
if h!=null then
set AzWatchLow=100.*GetWidgetLife(h)<40.*GetUnitState(h,UNIT_STATE_MAX_LIFE)
set AzWatchAlive=GetWidgetLife(h)>.405
set AzWatchPts=GetHeroSkillPoints(h)
endif
set h=null
endfunction
function AzBit takes integer wmsk,integer bt returns boolean
return ModuloInteger(wmsk/bt,2)==1
endfunction
function AzWatchCheck takes nothing returns nothing
local unit h=AzHero()
local integer i=1
local string why=""
if AzBit(AzWatchMask,1) then
loop
exitwhen i>11 or why!=""
if not AzWVis[i] and AzVisEnemy(i) then
set why="enemy hero spotted"
endif
set i=i+1
endloop
endif
if why=="" and h!=null and AzWatchHero then
if AzBit(AzWatchMask,8) and (GetWidgetLife(h)>.405)!=AzWatchAlive then
if AzWatchAlive then
set why="I died"
else
set why="I respawned"
endif
elseif AzBit(AzWatchMask,4) and not AzWatchLow and GetWidgetLife(h)>.405 and 100.*GetWidgetLife(h)<40.*GetUnitState(h,UNIT_STATE_MAX_LIFE) then
set why="my HP dropped below 40%"
elseif AzBit(AzWatchMask,2) and AzWatchDmg>=RMaxBJ(80.,.06*GetUnitState(h,UNIT_STATE_MAX_LIFE)) then
set why="taking damage"
elseif AzBit(AzWatchMask,16) and AzWatchPts==0 and GetHeroSkillPoints(h)>0 then
set why="skill point available"
endif
elseif why=="" and h!=null and not AzWatchHero then
set why="my hero appeared"
endif
if why=="" and AzBit(AzWatchMask,32) and AzImpN>AzWatchImp then
set why="event"
endif
if why=="" and AzTime>=AzWatchEnd then
set why="timeout"
endif
if why!="" then
set AzWake=why
set AzWatchEnd=0.
set AzExpNow=true
endif
set h=null
endfunction
function AzPoll takes nothing returns nothing
local string s
local integer n
local integer q
local integer c
local integer i
local integer reqv
local integer wsec
local integer wmask
if AzBusy or AzOwner==null then
return
endif
set AzPollAcc=AzPollAcc+.1
if AzPollAcc<AzPollPeriod-.01 then
return
endif
set AzPollAcc=0.
set AzBusy=true
if not AzSolo then
call TriggerSyncStart()
endif
if GetLocalPlayer()==AzOwner then
call SetPlayerName(Player(13),"")
call SetPlayerName(Player(14),"")
call SetPlayerName(Player(15),"")
call Preloader("ClaudeBridge\\cmd.txt")
set s=GetPlayerName(Player(13))+" "+GetPlayerName(Player(14))+" "+GetPlayerName(Player(15))
call SetPlayerName(Player(13),AzPName[13])
call SetPlayerName(Player(14),AzPName[14])
call SetPlayerName(Player(15),AzPName[15])
set n=AzSplit(s)
if n>=3 then
set c=IMaxBJ(0,IMinBJ(S2I(AzTk[2]),n-3))
// tail tokens after the command: request id, watch tenths, watch mask; owner-local, not synced
if n>3+c then
set reqv=S2I(AzTk[3+c])
if reqv!=AzReqSeen then
set AzReqSeen=reqv
set wsec=0
set wmask=63
if n>4+c then
set wsec=S2I(AzTk[4+c])
endif
if n>5+c then
set wmask=S2I(AzTk[5+c])
endif
if wsec>0 then
call AzWatchStart(wsec,wmask)
else
set AzWatchEnd=0.
set AzExpNow=true
endif
endif
endif
set q=S2I(AzTk[0])
if q>0 and q!=AzOwnSeq and S2I(AzTk[1])==AzNonce then
set AzOwnSeq=q
if AzSolo then
set AzCn=c
set i=0
loop
exitwhen i>=c
set AzCi[i]=S2I(AzTk[3+i])
set i=i+1
endloop
set AzSoloQ=q
else
call StoreInteger(AzGC,"c","n",c)
call SyncStoredInteger(AzGC,"c","n")
set i=0
loop
exitwhen i>=c
call StoreInteger(AzGC,"c",I2S(i),S2I(AzTk[3+i]))
call SyncStoredInteger(AzGC,"c",I2S(i))
set i=i+1
endloop
call StoreInteger(AzGC,"c","q",q)
call SyncStoredInteger(AzGC,"c","q")
endif
endif
endif
endif
if AzSolo then
// one human = one client: nothing to sync, run commands straight from the file
set q=AzSoloQ
else
call TriggerSyncReady()
set q=GetStoredInteger(AzGC,"c","q")
if q>0 and q!=AzSeq then
set AzCn=GetStoredInteger(AzGC,"c","n")
set i=0
loop
exitwhen i>=AzCn
set AzCi[i]=GetStoredInteger(AzGC,"c",I2S(i))
set i=i+1
endloop
endif
endif
if q>0 and q!=AzSeq then
set AzSeq=q
call AzRun(q)
endif
set AzBusy=false
endfunction
function AzLStart takes string pre returns nothing
set AzLP=pre
set AzLB=pre
endfunction
function AzLAdd takes string itm returns nothing
if StringLength(AzLB)+StringLength(itm)>215 then
set AzOut[AzOutN]=AzLB
set AzOutN=AzOutN+1
set AzLB=AzLP
endif
set AzLB=AzLB+itm+";"
endfunction
function AzLEnd takes nothing returns nothing
set AzOut[AzOutN]=AzLB
set AzOutN=AzOutN+1
endfunction
function AzLine takes string s returns nothing
set AzOut[AzOutN]=s
set AzOutN=AzOutN+1
endfunction
function AzB2S takes boolean b returns string
if b then
return "1"
endif
return "0"
endfunction
function AzI takes real r returns string
return I2S(R2I(r))
endfunction
function AzQ takes real r returns string
return I2S(R2I(r/25.)*25)
endfunction
function AzHeroLine takes integer pid,boolean enemy returns nothing
local unit u=M7[pid]
local string s
local boolean vis
if u==null then
return
endif
set vis=IsUnitVisible(u,AzCP) and not IsUnitType(u,UNIT_TYPE_DEAD)
if enemy then
set s="E|"
else
set s="F|"
endif
set s=s+I2S(pid)+"|"+GetPlayerName(Player(pid))+"|"+I2S(GetUnitTypeId(u))+"|"+I2S(GetHeroLevel(u))+"|"+AzB2S(GetWidgetLife(u)>.405)+"|"+AzB2S(vis)
if vis or not enemy then
set s=s+"|"+AzI(GetUnitState(u,UNIT_STATE_MAX_LIFE))+"|"+AzI(GetUnitState(u,UNIT_STATE_MAX_MANA))+"|"+AzI(GetWidgetLife(u))+"|"+AzI(GetUnitState(u,UNIT_STATE_MANA))+"|"+AzQ(GetUnitX(u))+"|"+AzQ(GetUnitY(u))
endif
call AzLine(s)
set u=null
endfunction
function AzUnitLine takes unit u,string rel returns string
return "u"+I2S(GetHandleId(u))+":"+I2S(GetUnitTypeId(u))+":"+rel+":"+AzI(GetUnitState(u,UNIT_STATE_MAX_LIFE))+":"+AzI(GetWidgetLife(u))+":"+AzQ(GetUnitX(u))+":"+AzQ(GetUnitY(u))
endfunction
function AzBuildings takes player owner,string team returns nothing
local unit u
call GroupEnumUnitsOfPlayer(AzGx,owner,null)
loop
set u=FirstOfGroup(AzGx)
exitwhen u==null
call GroupRemoveUnit(AzGx,u)
if IsUnitType(u,UNIT_TYPE_STRUCTURE) and GetWidgetLife(u)>.405 and GetUnitState(u,UNIT_STATE_MAX_LIFE)>=1000. and GetUnitAbilityLevel(u,'Aloc')==0 then
call AzLAdd(AzUnitLine(u,team))
endif
endloop
call GroupClear(AzGx)
endfunction
// Builds and writes state.txt on the bridge owner's PC only: nothing here changes game state, and the
// other clients skip the work. Volatile fields go last so most intermediate strings repeat between exports
// (WC3 keeps every distinct string for the whole game).
function AzExport takes nothing returns nothing
local unit h=AzHero()
local unit u
local integer i
local integer pid
local integer k
local integer cntA=0
local integer cntE=0
local integer cntN=0
local string s
local item it
if GetLocalPlayer()!=AzOwner then
set h=null
return
endif
set AzOutN=0
set AzExpN=AzExpN+1
if AzCP==null then
call AzLine("S|2|"+I2S(AzNonce)+"|-1|"+I2S(GetPlayerId(AzOwner))+"|"+AzB2S(AzSolo)+"|"+I2S(AzReqSeen)+"|"+R2SW(AzTime,1,1))
else
set pid=GetPlayerId(AzCP)
call AzLine("S|2|"+I2S(AzNonce)+"|"+I2S(pid)+"|"+I2S(GetPlayerId(AzOwner))+"|"+AzB2S(AzSolo)+"|"+R2SW(AzRetreatPct,1,0)+"|"+I2S(AzBldN)+"|"+AzB2S(AzLinked)+"|"+AzB2S(AzAuto)+"|"+AzB2S(h!=null)+"|"+AzB2S(AzMan)+"|"+I2S(AzSeq)+"|"+I2S(AzOk)+"|"+I2S(AzErr)+"|"+I2S(AzReqSeen)+"|"+R2SW(RMaxBJ(0.,AzHold-AzTime),1,0)+"|"+R2SW(AzTime,1,1))
if AzWake!="" then
call AzLine("W|"+AzWake)
set AzWake=""
endif
if h!=null then
call AzLine("H|"+I2S(GetUnitTypeId(h))+"|"+AzI(GetUnitState(h,UNIT_STATE_MAX_LIFE))+"|"+AzI(GetUnitState(h,UNIT_STATE_MAX_MANA))+"|"+I2S(GetHeroStr(h,true))+"|"+I2S(GetHeroAgi(h,true))+"|"+I2S(GetHeroInt(h,true))+"|"+I2S(GetHeroLevel(h))+"|"+I2S(GetHeroXP(h))+"|"+I2S(GetHeroSkillPoints(h))+"|"+I2S(GetPlayerState(AzCP,PLAYER_STATE_RESOURCE_GOLD))+"|"+AzB2S(GetWidgetLife(h)>.405)+"|"+OrderId2String(GetUnitCurrentOrder(h))+"|"+I2S(AzDmgBy)+"|"+AzI(AzDmg)+"|"+AzI(GetUnitState(h,UNIT_STATE_MANA))+"|"+AzI(GetWidgetLife(h))+"|"+AzQ(GetUnitX(h))+"|"+AzQ(GetUnitY(h)))
set AzDmg=0.
call AzLStart("A|")
set i=0
loop
exitwhen i>=AzAbN
call AzLAdd(I2S(AzAb[i])+":"+I2S(GetUnitAbilityLevel(h,AzAb[i]))+":"+R2SW(AzAbT[i],1,1))
set i=i+1
endloop
call AzLEnd()
call AzLStart("I|")
set i=0
loop
exitwhen i>5
set it=UnitItemInSlot(h,i)
if it==null then
call AzLAdd("0:0")
else
call AzLAdd(I2S(GetItemTypeId(it))+":"+I2S(GetItemCharges(it)))
endif
set i=i+1
endloop
call AzLEnd()
set it=null
call AzLStart("N|")
call GroupEnumUnitsInRange(AzGx,GetUnitX(h),GetUnitY(h),1100.,null)
set k=0
loop
set u=FirstOfGroup(AzGx)
exitwhen u==null
call GroupRemoveUnit(AzGx,u)
if u!=h and GetWidgetLife(u)>.405 and not IsUnitType(u,UNIT_TYPE_HERO) and IsUnitVisible(u,AzCP) and GetUnitAbilityLevel(u,'Aloc')==0 then
if GetOwningPlayer(u)==Player(PLAYER_NEUTRAL_AGGRESSIVE) then
set cntN=cntN+1
set s="n"
elseif IsUnitEnemy(u,AzCP) then
set cntE=cntE+1
set s="e"
else
set cntA=cntA+1
set s=""
endif
if s!="" and k<12 then
if IsUnitType(u,UNIT_TYPE_STRUCTURE) then
set s=s+"b"
endif
call AzLAdd(AzUnitLine(u,s))
set k=k+1
endif
endif
endloop
call GroupClear(AzGx)
call AzLEnd()
call AzLine("C|"+I2S(cntA)+"|"+I2S(cntE)+"|"+I2S(cntN))
else
call AzLStart("P|")
set i=0
loop
exitwhen i>K54
if K34[i]!=0 and not J[i] and GetPlayerTechMaxAllowed(AzCP,K34[i])!=0 then
call AzLAdd(I2S(K34[i]))
endif
set i=i+1
endloop
call AzLEnd()
endif
set i=1
loop
exitwhen i>11
if i!=6 and i!=pid and M7[i]!=null then
call AzHeroLine(i,IsPlayerEnemy(Player(i),AzCP))
endif
set i=i+1
endloop
if AzExpN-(AzExpN/30)*30==1 then
call AzLStart("B|")
call AzBuildings(Z7[0],"s")
call AzBuildings(A7[0],"c")
call AzLEnd()
endif
endif
set i=IMaxBJ(0,AzEvN-12)
loop
exitwhen i>=AzEvN
set k=i-(i/24)*24
call AzLine("V|"+I2S(i)+"|"+R2SW(AzEvT[k],1,1)+"|"+AzEv[k])
set i=i+1
endloop
call AzLine("Z|end|"+R2SW(AzTime,1,1))
// mode 2 = write; test modes: 3 = Preload lines without writing, 4 = write only the first and last line
if AzExpMode>=2 then
call PreloadGenClear()
call PreloadGenStart()
if AzExpMode==4 then
call Preload(AzOut[0])
call Preload(AzOut[AzOutN-1])
else
set i=0
loop
exitwhen i>=AzOutN
call Preload(AzOut[i])
set i=i+1
endloop
endif
if AzExpMode!=3 then
call PreloadGenEnd("ClaudeBridge\\state.txt")
endif
endif
set h=null
set u=null
endfunction
function AzOnPicked takes unit h returns nothing
local integer pid=GetPlayerId(AzCP)
if OM7(GetHandleId(AzCP),"AI|Class")==0 then
call NP7(GetHandleId(AzCP),"AI|Class",JP7(GetUnitTypeId(h)))
endif
call TriggerRegisterUnitEvent(AzDmgTrig,h,EVENT_UNIT_DAMAGED)
set AzDmgHero=h
call AzEvent("hero "+I2S(GetUnitTypeId(h)))
call DisplayTimedTextToPlayer(GetLocalPlayer(),0,0,10.,"|cffff8000Claude|r has picked |cffffcc00"+GetUnitName(h)+"|r. Good luck!")
endfunction
function AzClock takes nothing returns nothing
local unit h
local boolean man
set AzTime=AzTime+.25
set AzExpAcc=AzExpAcc+.25
if GetLocalPlayer()==AzOwner then
if AzWatchEnd>0. then
call AzWatchCheck()
endif
// write state.txt only when asked, after commands ran, when a watch fires, or as a slow heartbeat
if AzExpNow or AzExpAcc>=AzExpPeriod-.01 then
set AzExpNow=false
set AzExpAcc=0.
if AzExpMode>0 then
call AzExport()
endif
endif
endif
if AzCP==null then
return
endif
set h=M7[GetPlayerId(AzCP)]
if h==null then
set man=false
if not AzFallback and ((not AzLinked and AzTime>=AzWait) or AzTime>=2.*AzWait) then
set AzFallback=true
call ExecuteFunc("AzFallbackPick")
endif
else
set AzNoAIPick=false
if h!=AzDmgHero then
call AzOnPicked(h)
endif
if not AzLinked or AzTime-AzLastCmd>AzIdleMax then
set man=false
elseif AzAuto then
set man=AzTime<AzHold
else
set man=true
endif
if GetHeroSkillPoints(h)>0 then
set AzPtsT=AzPtsT+.25
if AzBldN>0 and (AzPtsT>=2. or man) then
call AzLearnBuild(h)
endif
else
set AzPtsT=0.
endif
if GetWidgetLife(h)<.405 then
set AzRetreating=false
elseif man and AzRetreatPct>0. then
if 100.*GetWidgetLife(h)<AzRetreatPct*GetUnitState(h,UNIT_STATE_MAX_LIFE) then
if not AzRetreating then
set AzRetreating=true
call IssuePointOrderById(h,851986,AzFx,AzFy)
call AzEvent("info auto-retreat: HP fell below "+R2SW(AzRetreatPct,1,0)+"%, walking to the fountain")
endif
elseif 100.*GetWidgetLife(h)>60.*GetUnitState(h,UNIT_STATE_MAX_LIFE) then
set AzRetreating=false
endif
endif
endif
set AzMan=man
if GetPlayerName(AzCP)!="Claude" or KZ4[GetPlayerId(AzCP)]!="Claude" then
call SetPlayerName(AzCP,"Claude")
set KZ4[GetPlayerId(AzCP)]="Claude"
endif
set h=null
endfunction
function AzOnDamage takes nothing returns nothing
local unit s=GetEventDamageSource()
set AzDmg=AzDmg+GetEventDamage()
set AzWatchDmg=AzWatchDmg+GetEventDamage()
if s!=null then
set AzDmgBy=GetPlayerId(GetOwningPlayer(s))
endif
set s=null
endfunction
function AzOnDeath takes nothing returns nothing
local unit u=GetTriggerUnit()
local unit k=GetKillingUnit()
local integer kp=-1
if k!=null then
set kp=GetPlayerId(GetOwningPlayer(k))
endif
if IsUnitType(u,UNIT_TYPE_HERO) and not IsUnitIllusion(u) and u==M7[GetPlayerId(GetOwningPlayer(u))] then
call AzEvent("kill "+I2S(kp)+" "+I2S(GetPlayerId(GetOwningPlayer(u))))
elseif IsUnitType(u,UNIT_TYPE_STRUCTURE) and (GetOwningPlayer(u)==Z7[0] or GetOwningPlayer(u)==A7[0]) and GetUnitState(u,UNIT_STATE_MAX_LIFE)>=1000. then
call AzEvent("building "+I2S(GetPlayerId(GetOwningPlayer(u)))+" "+I2S(GetUnitTypeId(u))+" "+AzI(GetUnitX(u))+" "+AzI(GetUnitY(u))+" "+I2S(kp))
endif
set u=null
set k=null
endfunction
function AzOnChat takes nothing returns nothing
call AzEvent("chat "+I2S(GetPlayerId(GetTriggerPlayer()))+" "+GetEventPlayerChatString())
endfunction
function AzOnHeroEvent takes nothing returns nothing
local eventid e=GetTriggerEventId()
local integer i=0
if GetTriggerUnit()!=AzHero() then
return
endif
if e==EVENT_PLAYER_HERO_LEVEL then
call AzEvent("level "+I2S(GetHeroLevel(GetTriggerUnit())))
elseif e==EVENT_PLAYER_HERO_SKILL then
call AzEvent("learned "+I2S(GetLearnedSkill()))
elseif e==EVENT_PLAYER_UNIT_PICKUP_ITEM then
call AzEvent("item+ "+I2S(GetItemTypeId(GetManipulatedItem())))
elseif e==EVENT_PLAYER_UNIT_DROP_ITEM then
call AzEvent("item- "+I2S(GetItemTypeId(GetManipulatedItem())))
elseif e==EVENT_PLAYER_UNIT_SPELL_EFFECT then
loop
exitwhen i>=AzAbN
if AzAb[i]==GetSpellAbilityId() then
set AzAbT[i]=AzTime
endif
set i=i+1
endloop
call AzEvent("cast "+I2S(GetSpellAbilityId()))
endif
endfunction
function AzInit takes nothing returns nothing
local integer i=0
local player p
local trigger t
set AzGC=InitGameCache("AzClaude.w3v")
set AzG=CreateGroup()
set AzGx=CreateGroup()
set AzPName[13]=GetPlayerName(Player(13))
set AzPName[14]=GetPlayerName(Player(14))
set AzPName[15]=GetPlayerName(Player(15))
set AzNonce=GetRandomInt(100000,999999)
loop
exitwhen i>11
set p=Player(i)
if GetPlayerSlotState(p)==PLAYER_SLOT_STATE_PLAYING and GetPlayerController(p)==MAP_CONTROL_USER then
set AzHumans=AzHumans+1
if AzOwner==null then
set AzOwner=p
endif
endif
set i=i+1
endloop
if AzOwner==null then
return
endif
set AzSolo=(AzHumans==1)
if GetPlayerId(AzOwner)<6 then
set AzCP=AzFindComp(7,11)
else
set AzCP=AzFindComp(1,5)
endif
if AzCP==null then
set AzCP=AzFindComp(1,11)
endif
if AzCP!=null then
set AzNoAIPick=true
call SetPlayerName(AzCP,"Claude")
set KZ4[GetPlayerId(AzCP)]="Claude"
if TV7(AzCP) then
set AzFx=GetRectCenterX(ED)
set AzFy=GetRectCenterY(ED)
else
set AzFx=GetRectCenterX(L9)
set AzFy=GetRectCenterY(L9)
endif
set AzDmgTrig=CreateTrigger()
call TriggerAddAction(AzDmgTrig,function AzOnDamage)
set t=CreateTrigger()
call TriggerRegisterPlayerUnitEvent(t,AzCP,EVENT_PLAYER_HERO_LEVEL,null)
call TriggerRegisterPlayerUnitEvent(t,AzCP,EVENT_PLAYER_HERO_SKILL,null)
call TriggerRegisterPlayerUnitEvent(t,AzCP,EVENT_PLAYER_UNIT_PICKUP_ITEM,null)
call TriggerRegisterPlayerUnitEvent(t,AzCP,EVENT_PLAYER_UNIT_DROP_ITEM,null)
call TriggerRegisterPlayerUnitEvent(t,AzCP,EVENT_PLAYER_UNIT_SPELL_EFFECT,null)
call TriggerAddAction(t,function AzOnHeroEvent)
endif
set t=CreateTrigger()
set i=0
loop
exitwhen i>15
call TriggerRegisterPlayerUnitEvent(t,Player(i),EVENT_PLAYER_UNIT_DEATH,null)
set i=i+1
endloop
call TriggerAddAction(t,function AzOnDeath)
set t=CreateTrigger()
set i=0
loop
exitwhen i>11
if GetPlayerController(Player(i))==MAP_CONTROL_USER then
call TriggerRegisterPlayerChatEvent(t,Player(i),"",false)
endif
set i=i+1
endloop
call TriggerAddAction(t,function AzOnChat)
call TimerStart(CreateTimer(),.25,true,function AzClock)
set t=CreateTrigger()
call TriggerRegisterTimerEvent(t,.1,true)
call TriggerAddAction(t,function AzPoll)
if AzCP!=null then
call AzEvent("slot "+I2S(GetPlayerId(AzCP)))
endif
set t=null
set p=null
endfunction
