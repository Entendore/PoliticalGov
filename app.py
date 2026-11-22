import pygame, numpy as np, random, math
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import List, Tuple, Optional, Callable, Dict, Set

SEED = 1337
random.seed(SEED); np.random.seed(SEED)
WIDTH, HEIGHT = 1280, 800
FPS = 60
MAX_TURNS = 30

# Palette
COL_BG=(12,15,24); COL_BG_GRAD=(24,28,42); COL_PANEL=(22,26,38); COL_PANEL_LIGHT=(36,42,60); COL_PANEL_DARK=(16,19,30)
COL_GOLD=(218,178,92); COL_GOLD_BR=(245,210,130); COL_RED=(210,70,70); COL_RED_BR=(245,100,100)
COL_GREEN=(90,190,120); COL_GREEN_BR=(130,230,160); COL_BLUE=(100,150,220); COL_PURPLE=(160,110,220)
COL_ORANGE=(230,150,70); COL_TEAL=(80,180,180); COL_PINK=(220,120,170); COL_CYAN=(100,200,220)
COL_TEXT=(225,225,235); COL_TEXT_DIM=(140,145,165); COL_TEXT_BR=(250,250,255)
COL_BORDER=(60,65,85); COL_BORDER_BR=(100,110,140)

RES_COL = {"treasury":COL_GOLD, "influence":COL_PURPLE, "happiness":COL_GREEN, "stability":COL_BLUE, "military":COL_RED}
RES_NAME = {"treasury":"TREASURY", "influence":"INFLUENCE", "happiness":"HAPPINESS", "stability":"STABILITY", "military":"MILITARY"}
RES_DESC = {"treasury":"Gold reserves. Funds armies, relief, and bribes.", "influence":"Soft power and diplomatic clout abroad.",
            "happiness":"Popular support. Zero means revolution.", "stability":"Internal order. Zero means collapse.", "military":"Armed forces. Zero invites invasion."}
RES_ORDER = ["treasury", "influence", "happiness", "stability", "military"]

RULER_NAMES = ["Aethelgard","Balthazar","Cleomedes","Drusilla","Eldric","Fenrir","Gwendolyn","Hadrian","Isolde","Jovan","Kaelen","Lysander","Morgaine","Nestor","Octavia","Pompey"]
DYNASTY_NAMES = ["Blackwood","Stormrider","Goldcrest","Ironheart","Shadowmend","Wyrmguard","Silverblood","Highspire","Ravencrest","Stoutfoot"]
RIVAL_NAMES = ["The Shadow Council","Lord Malakor","The Crimson Cabal","General Grimm","The Silent Hand"]

FOREIGN_POWERS = [
    {"name":"VANDRIA","color":COL_RED,"bonus_key":"military","bonus_val":2},
    {"name":"KRASSIA","color":COL_GOLD,"bonus_key":"treasury","bonus_val":3},
    {"name":"MERIDIA","color":COL_TEAL,"bonus_key":"influence","bonus_val":2}
]

class GovType(Enum): DEMOCRACY=auto(); DICTATORSHIP=auto(); MONARCHY=auto(); OLIGARCHY=auto(); THEOCRACY=auto(); COMMUNISM=auto()
GOV_TITLES = {GovType.DEMOCRACY:"President", GovType.DICTATORSHIP:"Supreme Leader", GovType.MONARCHY:"Monarch", GovType.OLIGARCHY:"Prime Magnate", GovType.THEOCRACY:"High Priest", GovType.COMMUNISM:"First Secretary"}

def ease_out_cubic(t): return 1 - (1 - t) ** 3
def ease_in_cubic(t): return t ** 3
def ease_in_out_cubic(t): return 4*t**3 if t < 0.5 else 1 - (-2*t + 2)**3 / 2
def ease_out_back(t):
    c1 = 1.70158; c3 = c1 + 1; return 1 + c3 * (t - 1) ** 3 + c1 * (t - 1) ** 2
def lerp(a, b, t): return a + (b - a) * t
def lerp_color(c1, c2, t): return (int(lerp(c1[0],c2[0],t)), int(lerp(c1[1],c2[1],t)), int(lerp(c1[2],c2[2],t)))
def clamp(v, mn, mx): return max(mn, min(mx, v))

@dataclass
class Government:
    name: str; type: GovType; color: Tuple[int,int,int]; description: str; tagline: str; bonus: str
    start: Dict[str,int]; drift: Dict[str,int]

GOVERNMENTS = [
    Government("DEMOCRACY", GovType.DEMOCRACY, (100,150,220), "Power flows from the people.", "By the people, for the people.", "Happiness holds steady.", {"treasury":50,"influence":50,"happiness":70,"stability":60,"military":45}, {"happiness":-1}),
    Government("DICTATORSHIP", GovType.DICTATORSHIP, (210,70,70), "One ruler, absolute power.", "Power from the barrel of a gun.", "Military strength each year.", {"treasury":50,"influence":50,"happiness":40,"stability":55,"military":70}, {"happiness":-2,"military":1}),
    Government("MONARCHY", GovType.MONARCHY, (218,178,92), "Royal bloodline rules.", "The crown is heavy, but it is mine.", "Stability accumulates.", {"treasury":60,"influence":55,"happiness":55,"stability":70,"military":50}, {"stability":1,"treasury":1}),
    Government("OLIGARCHY", GovType.OLIGARCHY, (160,110,220), "Wealthy elites govern.", "Gold speaks louder than decrees.", "Treasury grows fast.", {"treasury":75,"influence":55,"happiness":45,"stability":55,"military":45}, {"treasury":2,"happiness":-1}),
    Government("THEOCRACY", GovType.THEOCRACY, (220,200,100), "Divine mandate.", "Vessels of the divine will.", "Influence rises from faith.", {"treasury":50,"influence":70,"happiness":60,"stability":55,"military":50}, {"influence":1}),
    Government("COMMUNISM", GovType.COMMUNISM, (220,80,80), "Workers own the means.", "From each by ability, to each by need.", "Strong military. Economy struggles.", {"treasury":40,"influence":50,"happiness":60,"stability":55,"military":65}, {"treasury":-1,"military":1,"happiness":1})
]

POLICIES = [
    {"name":"ECONOMIC REFORM","color":COL_GOLD,"description":"Lower taxes, deregulate markets.","effects":"+2 T/turn, -1 H/turn","drift":{"treasury":2,"happiness":-1}},
    {"name":"MILITARY EXPANSION","color":COL_RED,"description":"Expand armed forces.","effects":"+2 M/turn, -1 T/turn","drift":{"military":2,"treasury":-1}},
    {"name":"CULTURAL RENAISSANCE","color":COL_GREEN,"description":"Patronize the arts.","effects":"+2 H/turn, -1 T/turn","drift":{"happiness":2,"treasury":-1}},
    {"name":"DIPLOMATIC CORPS","color":COL_PURPLE,"description":"Establish embassies.","effects":"+2 I/turn, -1 M/turn","drift":{"influence":2,"military":-1}}
]

RESEARCH_UPGRADES = [
    {"name":"CIVIL SERVICE","desc":"Bureaucrats stabilize the realm.","drift":{"stability":1},"color":COL_BLUE},
    {"name":"MERCANTILISM","desc":"State monopolies enrich treasury.","drift":{"treasury":2,"happiness":-1},"color":COL_GOLD},
    {"name":"STANDING ARMY","desc":"Professional force trains year-round.","drift":{"military":2,"treasury":-1},"color":COL_RED},
    {"name":"PATRONAGE","desc":"Funding arts pleases masses.","drift":{"happiness":2,"treasury":-1},"color":COL_GREEN},
    {"name":"ENVOYS","desc":"Diplomats spread influence.","drift":{"influence":2,"treasury":-1},"color":COL_PURPLE},
    {"name":"SECRET POLICE","desc":"Spies root out sedition.","drift":{"rival":-2,"happiness":-1},"color":COL_ORANGE}
]

TRADE_ROUTES = [
    {"name":"SPICE ROUTE","desc":"Lucrative food and spice trade.","drift":{"treasury":3},"color":COL_GOLD},
    {"name":"SILK ROUTE","desc":"Exotic fabrics and culture.","drift":{"influence":2,"happiness":1},"color":COL_PURPLE},
    {"name":"IRON ROUTE","desc":"Weapons and raw materials.","drift":{"military":2,"treasury":1},"color":COL_RED}
]

PROJECTS = [
    {"name":"ROYAL MINT","desc":"Boosts treasury permanently.","drift":{"treasury":2},"color":COL_GOLD},
    {"name":"WAR COLLEGE","desc":"Trains elite officers.","drift":{"military":2},"color":COL_RED},
    {"name":"GRAND CATHEDRAL","desc":"Inspires faith and loyalty.","drift":{"happiness":2,"influence":1},"color":COL_GREEN},
    {"name":"CITY WALLS","desc":"Defends against raids.","drift":{"stability":2,"rival":-1},"color":COL_BLUE},
    {"name":"SPIRAL ARCHIVE","desc":"Center of learning.","drift":{"influence":2,"happiness":1},"color":COL_TEAL}
]

DEFAULT_COURT = [
    {"name":"Sir Garrick","role":"MARSHAL","drift":{"military":1,"stability":1},"color":COL_RED,"boon":"MARTIAL LAW"},
    {"name":"Lady Meridia","role":"CHANCELLOR","drift":{"influence":1,"happiness":1},"color":COL_PURPLE,"boon":"DIPLOMATIC ENVOY"},
    {"name":"Master Tolvin","role":"STEWARD","drift":{"treasury":1,"stability":1},"color":COL_GOLD,"boon":"EMERGENCY FUNDS"}
]
COURT_CANDIDATES = [
    {"name":"Duke Vex","role":"MARSHAL","drift":{"military":2,"happiness":-1},"color":COL_RED,"boon":"MARTIAL LAW"},
    {"name":"Lady Elara","role":"CHANCELLOR","drift":{"influence":2,"treasury":-1},"color":COL_PURPLE,"boon":"DIPLOMATIC ENVOY"},
    {"name":"Brother Corvo","role":"STEWARD","drift":{"treasury":3,"happiness":-2},"color":COL_GOLD,"boon":"EMERGENCY FUNDS"},
    {"name":"Sir Kaelen","role":"MARSHAL","drift":{"stability":1,"military":1},"color":COL_BLUE,"boon":"MARTIAL LAW"},
    {"name":"Sister Lyra","role":"CHANCELLOR","drift":{"happiness":1,"influence":1},"color":COL_GREEN,"boon":"DIPLOMATIC ENVOY"},
    {"name":"Merchant Roark","role":"STEWARD","drift":{"treasury":2,"influence":1},"color":COL_ORANGE,"boon":"EMERGENCY FUNDS"}
]

DECREES = [
    {"name":"HOLD GAMES","cost":15,"effects":{"treasury":-15,"happiness":10,"stability":-5},"color":COL_GREEN},
    {"name":"LEVY TROOPS","cost":15,"effects":{"treasury":-15,"military":10,"happiness":-5},"color":COL_RED},
    {"name":"SEND GIFTS","cost":15,"effects":{"treasury":-15,"influence":10,"military":-5},"color":COL_PURPLE},
    {"name":"FORTIFY","cost":15,"effects":{"treasury":-15,"stability":10,"happiness":-5},"color":COL_BLUE},
    {"name":"SECRET POLICE","cost":20,"effects":{"treasury":-20,"stability":5},"color":COL_ORANGE,"modifiers":[{"name":"SECRET POLICE","desc":"Suppressing rivals","duration":3,"drift":{"rival":-5,"happiness":-1},"color":COL_ORANGE}]},
    {"name":"TRADE PACT","cost":15,"effects":{"treasury":-15,"influence":5},"color":COL_CYAN,"foreign":{"vandria":8,"krassia":8,"meridia":8}},
    {"name":"ESPIONAGE","cost":0,"effects":{"treasury":20},"color":COL_PINK,"foreign":{"rand":-15}}
]
DECREE_KEYS = [pygame.K_q, pygame.K_w, pygame.K_e, pygame.K_r, pygame.K_t, pygame.K_y, pygame.K_u]

PROPHECIES = [
    {"name":"GOLDEN PATH","desc":"Maintain Treasury > 60","reward":{"treasury":20,"happiness":10},"penalty":{"treasury":-20},"color":COL_GOLD},
    {"name":"IRON FIST","desc":"Maintain Stability > 70","reward":{"rival":-20,"military":10},"penalty":{"stability":-10},"color":COL_RED},
    {"name":"PEOPLE'S VOICE","desc":"Maintain Happiness > 60","reward":{"influence":10},"penalty":{"happiness":-10},"color":COL_GREEN},
    {"name":"CULTURAL ZENITH","desc":"Maintain Influence > 60","reward":{"happiness":10,"treasury":10},"penalty":{"influence":-10},"color":COL_PURPLE},
    {"name":"SPARTAN WAY","desc":"Maintain Military > 70","reward":{"stability":10,"rival":-10},"penalty":{"military":-10},"color":COL_BLUE}
]

@dataclass
class Choice:
    text: str; effects: Dict[str,int]; modifiers: List[Dict] = field(default_factory=list)
    queue: Optional[str] = None; foreign: Dict[str,int] = field(default_factory=dict); check: Optional[Dict] = None

@dataclass
class Event:
    title: str; description: str; choices: List[Choice]
    category: str = "SOCIAL"; gov_types: Optional[Set[GovType]] = None
    is_crisis: bool = False; condition: Optional[Callable] = None; event_id: Optional[str] = None

EVENTS = [
    Event("FAMINE STRIKES","A severe drought has withered crops. Citizens grow desperate.",
          [Choice("Emergency food relief",{"treasury":-25,"happiness":15,"stability":5}), Choice("Ignore the crisis",{"happiness":-25,"stability":-10},foreign={"vandria":-5}), Choice("Seize foreign grain",{"military":-10,"happiness":10,"influence":-15},foreign={"vandria":-15,"krassia":-10,"meridia":-5})],"CRISIS",is_crisis=True),
    Event("BORDER SKIRMISH","Hostile forces probe your borders. A minor incursion has occurred.",
          [Choice("Send the army",{"military":-15,"stability":5,"influence":10},foreign={"vandria":-10},check={"stat":"military","success":{"military":5,"influence":10},"failure":{"military":-10,"stability":-5}}), Choice("Diplomatic protest",{"influence":5,"stability":-5},foreign={"vandria":-5}), Choice("Pay them off",{"treasury":-30,"stability":5})],"MILITARY"),
    Event("ECONOMIC BOOM","Trade routes flourish. The treasury swells with revenue.",
          [Choice("Invest in military",{"treasury":20,"military":15}), Choice("Invest in people",{"treasury":20,"happiness":15}), Choice("Stash the surplus",{"treasury":50,"happiness":-5})],"ECONOMIC"),
    Event("CORRUPTION SCANDAL","A high official has been embezzling state funds.",
          [Choice("Public execution",{"happiness":10,"stability":-5,"influence":-10}), Choice("Quiet cover-up",{"treasury":-20,"influence":5,"rival":10}), Choice("Full investigation",{"treasury":-10,"influence":-15,"stability":5})],"SOCIAL"),
    Event("CIVIL UNREST","Protests erupt in the capital. Citizens demand reform.",
          [Choice("Concede to demands",{"happiness":15,"treasury":-20}), Choice("Crush the protest",{"military":-5,"happiness":-20,"stability":-10}), Choice("Negotiate",{"influence":-10,"happiness":5,"stability":5})],"CRISIS",is_crisis=True),
    Event("FOREIGN DIPLOMAT","An envoy from Krassia arrives offering a trade agreement.",
          [Choice("Sign the treaty",{"treasury":25,"influence":10},foreign={"krassia":15}), Choice("Demand better terms",{"influence":15,"stability":-5},foreign={"krassia":-5}), Choice("Reject them",{"influence":-10,"military":5},foreign={"krassia":-15})],"DIPLOMATIC"),
    Event("PLAGUE SPREADS","A mysterious illness sweeps through the cities.",
          [Choice("Quarantine cities",{"happiness":-10,"stability":10,"treasury":-15},check={"stat":"stability","success":{"stability":5},"failure":{"happiness":-10,"stability":-5}}), Choice("Seek foreign aid",{"influence":-10,"happiness":5},foreign={"vandria":5,"krassia":5,"meridia":5}), Choice("Pray for deliverance",{"happiness":-20,"stability":-10})],"CRISIS",is_crisis=True),
    Event("ESPIONAGE UNCOVERED","Foreign spies from Vandria have infiltrated your court.",
          [Choice("Execute spies",{"military":5,"influence":-10},foreign={"vandria":-20}), Choice("Turn them double",{"influence":15,"stability":-5,"rival":-15},foreign={"vandria":-5},check={"stat":"influence","success":{"rival":-20,"influence":10},"failure":{"stability":-10,"rival":10}}), Choice("Expel quietly",{"influence":5,"treasury":-10},foreign={"vandria":-10})],"DIPLOMATIC"),
    Event("MARKET CRASH","The economy contracts sharply. Panic spreads.",
          [Choice("Stimulus package",{"treasury":-30,"happiness":10}), Choice("Austerity measures",{"treasury":10,"happiness":-20}), Choice("Blame foreigners",{"influence":-10,"military":5},foreign={"krassia":-10})],"ECONOMIC"),
    Event("NOBLE PLOT","A cabal of nobles conspires to seize power.",
          [Choice("Execute ringleaders",{"military":5,"stability":-10,"rival":-10}), Choice("Offer concessions",{"treasury":-20,"influence":5,"rival":10}), Choice("Covertly eliminate",{"influence":-5,"stability":5,"military":-5,"rival":-20})],"CRISIS",is_crisis=True),
    Event("MILITARY VICTORY","Your generals return triumphant from a foreign campaign.",
          [Choice("Reward soldiers",{"treasury":-15,"military":15,"happiness":5}), Choice("Claim spoils",{"treasury":35,"military":-5}), Choice("Hold a triumph",{"treasury":-10,"happiness":15,"influence":10})],"MILITARY"),
    Event("DYNASTIC MARRIAGE","Meridia offers their royal heir in marriage.",
          [Choice("Accept match",{"influence":15,"stability":5,"treasury":10},foreign={"meridia":20}), Choice("Demand terms",{"influence":10,"stability":-5},foreign={"meridia":-5}), Choice("Reject politely",{"influence":-5,"military":5},foreign={"meridia":-15})],"DIPLOMATIC"),
    Event("PHILOSOPHER'S CHALLENGE","A radical thinker questions your rule in pamphlets.",
          [Choice("Ban writings",{"influence":5,"happiness":-10}), Choice("Debate publicly",{"influence":-5,"happiness":10,"stability":5},check={"stat":"influence","success":{"happiness":15,"influence":10},"failure":{"influence":-10,"stability":-5}}), Choice("Buy silence",{"treasury":-20,"influence":5})],"SOCIAL"),
    Event("ELECTION SEASON","Campaigns rage. Rivals attack your record.",
          [Choice("Spend on campaign",{"treasury":-25,"happiness":10,"influence":10}), Choice("Debate rivals",{"influence":15,"stability":-5}), Choice("Suppress opposition",{"happiness":-15,"stability":5,"influence":-10})],"SOCIAL",gov_types={GovType.DEMOCRACY}),
    Event("COURT INTRIGUE","Rival generals whisper you have grown weak.",
          [Choice("Purge generals",{"military":-15,"stability":10,"rival":-15}), Choice("Buy loyalty",{"treasury":-30,"military":5,"rival":5}), Choice("Ignore whispers",{"stability":-10,"military":-5,"rival":15})],"MILITARY",gov_types={GovType.DICTATORSHIP}),
    Event("ROYAL HEIR","Your firstborn comes of age. Succession must be secured.",
          [Choice("Grand coronation",{"treasury":-30,"stability":15,"happiness":10}), Choice("Quiet ceremony",{"treasury":-10,"stability":5}), Choice("Delay ceremony",{"stability":-10,"happiness":-5})],"SPECIAL",gov_types={GovType.MONARCHY}),
    Event("MONOPOLY THREAT","A consortium threatens to corner the grain market.",
          [Choice("Break monopoly",{"treasury":-15,"happiness":15}), Choice("Tax consortium",{"treasury":25,"influence":-5}), Choice("Partner with them",{"treasury":15,"happiness":-10})],"ECONOMIC",gov_types={GovType.OLIGARCHY}),
    Event("HOLY WAR CALL","Religious leaders call for a crusade against Vandria.",
          [Choice("Answer call",{"military":-15,"influence":20,"happiness":10},foreign={"vandria":-25}), Choice("Token forces",{"military":-5,"influence":5},foreign={"vandria":-10}), Choice("Deny priests",{"influence":-20,"happiness":-10})],"MILITARY",gov_types={GovType.THEOCRACY}),
    Event("PARTY PURGE","Hardliners demand a purge of reformists.",
          [Choice("Execute purge",{"stability":10,"happiness":-15,"influence":-5,"rival":-20}), Choice("Re-educate",{"treasury":-15,"happiness":-5,"stability":5}), Choice("Ignore them",{"stability":-10,"military":-5,"rival":15})],"CRISIS",gov_types={GovType.COMMUNISM},is_crisis=True),
    Event("REVOLUTION","The streets run red with fire. The people demand your head.",
          [Choice("Mobilize loyalists",{"military":-20,"happiness":-10,"stability":10}), Choice("Flee capital",{"influence":-20,"stability":-10,"treasury":-20}), Choice("Abdicate",{"influence":-30,"happiness":10})],"CRISIS",is_crisis=True,condition=lambda g: g.resources["happiness"]<=15 and g.resources["stability"]<=15 and g.turn>3),
    Event("MILITARY COUP","Generals march on the capital. Tanks surround the palace.",
          [Choice("Crush coup",{"military":-30,"stability":-5}), Choice("Surrender power",{"influence":-20,"stability":5,"military":-10}), Choice("Buy off generals",{"treasury":-40,"military":-5,"stability":5})],"CRISIS",is_crisis=True,condition=lambda g: g.resources["stability"]<=20 and g.resources["military"]>=70 and g.turn>5),
    Event("ANCIENT TOMB DISCOVERED","Excavators unearth a vast tomb of an ancient king.",
          [Choice("Break the seal",{"treasury":30,"stability":-10},queue="tomb_curse"), Choice("Seal forever",{"stability":10,"influence":5})],"SPECIAL",event_id="tomb_1"),
    Event("THE TOMB CURSE","A dark plague escapes the tomb. Shadows move on their own.",
          [Choice("Hire priests",{"treasury":-20,"happiness":10}), Choice("Embrace power",{"military":15,"happiness":-20},queue="shadow_legion")],"CRISIS",is_crisis=True,event_id="tomb_curse"),
    Event("SHADOW LEGION","The ancient king offers an army of invincible shadow soldiers.",
          [Choice("Unleash legion",{"military":25,"stability":-15,"happiness":-10}), Choice("Destroy legion",{"military":-10,"influence":15,"happiness":10})],"MILITARY",event_id="shadow_legion"),
    Event("VANDRIAN ULTIMATUM","Vandria demands tribute or threatens war.",
          [Choice("Pay tribute",{"treasury":-30,"influence":-5},foreign={"vandria":10}), Choice("Defy them",{"military":10,"stability":-10},foreign={"vandria":-20}), Choice("Counter-proposal",{"influence":10,"treasury":-15},foreign={"vandria":5})],"CRISIS",is_crisis=True,condition=lambda g: g.foreign_relations[0]<40 and g.turn>4),
    Event("PEACE SUMMIT","Meridia hosts a peace summit. All powers will attend.",
          [Choice("Attend",{"influence":20,"treasury":-10},foreign={"vandria":10,"krassia":10,"meridia":15}), Choice("Send proxy",{"influence":5},foreign={"meridia":-5}), Choice("Boycott",{"influence":-10},foreign={"vandria":-5,"krassia":-5,"meridia":-10})],"DIPLOMATIC")
]

class GameState(Enum): MENU=auto(); GOV_SELECT=auto(); POLICY_SELECT=auto(); PLAYING=auto(); PAUSED=auto(); GAME_OVER=auto(); VICTORY=auto()
class TurnPhase(Enum): INTRO=auto(); ACTIVE=auto(); EFFECTS=auto(); TRANSITION=auto(); OUTRO=auto()

class Tween:
    def __init__(self, obj, attr, start, end, duration, easing_func=ease_out_cubic):
        self.obj = obj
        self.attr = attr
        self.start = start
        self.end = end
        self.duration = duration
        self.elapsed = 0
        self.easing_func = easing_func
        self.done = False

    def update(self, dt):
        self.elapsed += dt
        if self.elapsed >= self.duration:
            self.elapsed = self.duration
            self.done = True
        t = self.elapsed / self.duration
        val = self.start + (self.end - self.start) * self.easing_func(t)
        
        if isinstance(self.obj, dict):
            self.obj[self.attr] = val
        else:
            setattr(self.obj, self.attr, val)
        return self.done

@dataclass
class Modifier:
    name: str
    description: str
    duration: int
    max_duration: int
    drift: Dict[str, int]
    color: Tuple[int, int, int]
    pulse_t: float = 0.0

class SoundManager:
    def __init__(self):
        self.enabled=True; self.muted=False; self.sounds={}; self.wind_playing=False
        try:
            pygame.mixer.pre_init(44100,-16,2,256); pygame.mixer.init(); self._gen()
        except: self.enabled=False
    def _make(self, s):
        if not self.enabled: return None
        s=np.clip(s,-1,1); st=np.column_stack([s,s]); return pygame.sndarray.make_sound((st*32767).astype(np.int16))
    def _gen(self):
        sr=44100; t=np.arange(int(sr*0.05))/sr; env=np.exp(-t*30); self.sounds['click']=self._make(0.3*env*np.sin(2*np.pi*880*t))
        t=np.arange(int(sr*0.03))/sr; env=np.exp(-t*50); self.sounds['hover']=self._make(0.1*env*np.sin(2*np.pi*1200*t))
        t=np.arange(int(sr*0.35))/sr; env=np.exp(-t*4); f=440+880*t; self.sounds['positive']=self._make(0.3*env*np.sin(2*np.pi*f*t))
        t=np.arange(int(sr*0.45))/sr; env=np.exp(-t*3); n=np.random.uniform(-1,1,len(t)); to=np.sin(2*np.pi*100*t)+0.5*np.sin(2*np.pi*80*t); self.sounds['negative']=self._make(0.35*env*(0.6*to+0.4*n))
        t=np.arange(int(sr*0.6))/sr; env=np.exp(-t*2.5); to=np.sin(2*np.pi*60*t)+0.7*np.sin(2*np.pi*45*t); n=np.random.uniform(-1,1,len(t))*0.5; self.sounds['crisis']=self._make(0.4*env*(to+n))
        t=np.arange(int(sr*1.5))/sr; env=np.exp(-t*1.2); f=300-200*t; self.sounds['game_over']=self._make(0.4*env*np.sin(2*np.pi*f*t))
        t=np.arange(int(sr*1.2))/sr; env=np.exp(-t*1.0); w=(np.sin(2*np.pi*523*t)+np.sin(2*np.pi*659*t)+np.sin(2*np.pi*784*t))/3; self.sounds['victory']=self._make(0.35*env*w)
        t=np.arange(int(sr*0.06))/sr; env=np.exp(-t*25); self.sounds['tick']=self._make(0.2*env*np.sin(2*np.pi*660*t))
        t=np.arange(int(sr*0.3))/sr; env=np.exp(-t*6)*(1-np.exp(-t*30)); n=np.random.uniform(-1,1,len(t)); self.sounds['whoosh']=self._make(0.18*env*n)
        t=np.arange(int(sr*0.8))/sr; env=np.exp(-t*2); w=(np.sin(2*np.pi*659*t)+np.sin(2*np.pi*880*t)+np.sin(2*np.pi*1047*t))/3; self.sounds['milestone']=self._make(0.4*env*w)
        t=np.arange(int(sr*0.4))/sr; env=np.exp(-t*3); f=330+400*t; self.sounds['policy']=self._make(0.3*env*np.sin(2*np.pi*f*t))
        t=np.arange(int(sr*0.5))/sr; env=np.exp(-t*2.5); w=np.sin(2*np.pi*400*t)+np.sin(2*np.pi*600*t); self.sounds['transition']=self._make(0.25*env*w)
        t=np.arange(int(sr*0.6))/sr; env=np.exp(-t*2); w=np.sin(2*np.pi*523*t)+np.sin(2*np.pi*784*t); self.sounds['research']=self._make(0.35*env*w)
        t=np.arange(int(sr*0.2))/sr; env=np.exp(-t*8); w=np.sin(2*np.pi*880*t)+np.sin(2*np.pi*1320*t); self.sounds['nudge']=self._make(0.3*env*w)
        t=np.arange(int(sr*0.8))/sr; env=np.exp(-t*2); n=np.random.uniform(-1,1,len(t))*0.7; to=np.sin(2*np.pi*80*t)+np.sin(2*np.pi*55*t); self.sounds['war']=self._make(0.5*env*(to+n))
        t=np.arange(int(sr*0.5))/sr; env=np.exp(-t*3); w=np.sin(2*np.pi*660*t)+np.sin(2*np.pi*990*t); self.sounds['diplomacy']=self._make(0.3*env*w)
        t=np.arange(int(sr*0.7))/sr; env=np.exp(-t*2); w=np.sin(2*np.pi*440*t)+np.sin(2*np.pi*554*t)+np.sin(2*np.pi*659*t); self.sounds['boon']=self._make(0.4*env*w)
        t=np.arange(int(sr*2.0))/sr
        wind = np.convolve(np.random.uniform(-1, 1, len(t)), np.ones(100)/100, mode='same')
        self.sounds['wind'] = self._make(0.15 * wind)
        # Prophecy sound
        t=np.arange(int(sr*1.0))/sr
        env=np.exp(-t*1.5)
        w=np.sin(2*np.pi*330*t) + np.sin(2*np.pi*440*t)*0.5
        self.sounds['prophecy']=self._make(0.4*env*w)
    def play(self, name, vol=1.0):
        if not self.enabled or self.muted: return
        s=self.sounds.get(name)
        if s: s.set_volume(vol); s.play()
    def update_weather_sound(self, weather):
        if not self.enabled: return
        if weather in ['rain', 'snow', 'ash'] and not self.muted:
            if not self.wind_playing:
                self.sounds['wind'].play(loops=-1)
                self.wind_playing = True
        else:
            if self.wind_playing:
                self.sounds['wind'].stop()
                self.wind_playing = False

class Particle:
    def __init__(self, x, y, vx, vy, life, color, size, gravity=0, shape='circle', drag=0.95):
        self.x=x;self.y=y;self.vx=vx;self.vy=vy;self.life=life;self.max_life=life;self.color=color;self.size=size
        self.gravity=gravity;self.shape=shape;self.drag=drag;self.rotation=random.uniform(0,math.pi*2);self.rot_speed=random.uniform(-5,5)
    def update(self, dt):
        self.x+=self.vx*dt; self.y+=self.vy*dt; self.vy+=self.gravity*dt; self.vx*=self.drag; self.life-=dt; self.rotation+=self.rot_speed*dt
    def draw(self, surf):
        if self.life<=0: return
        a=clamp(self.life/self.max_life,0,1); r=max(1,int(self.size*(0.5+0.5*a))); col=(*self.color,int(255*a))
        if self.shape=='circle':
            s=pygame.Surface((r*2+2,r*2+2),pygame.SRCALPHA); pygame.draw.circle(s,col,(r+1,r+1),r); surf.blit(s,(self.x-r-1,self.y-r-1))
        elif self.shape=='star':
            s=pygame.Surface((r*4,r*4),pygame.SRCALPHA); cx,cy=r*2,r*2; pts=[]
            for i in range(10):
                ang=self.rotation+i*math.pi/5; rad=r*2 if i%2==0 else r; pts.append((cx+math.cos(ang)*rad,cy+math.sin(ang)*rad))
            pygame.draw.polygon(s,col,pts); surf.blit(s,(self.x-cx,self.y-cy))

class FloatingText:
    def __init__(self, x, y, text, color, life=1.2, vy=-60, size=24):
        self.x=x;self.y=y;self.text=text;self.color=color;self.life=life;self.max_life=life;self.vy=vy;self.size=size;self.scale=0
    def update(self, dt):
        self.y+=self.vy*dt; self.vy*=0.96; self.life-=dt; t=1-self.life/self.max_life; self.scale=ease_out_back(min(1,t*4))
    def draw(self, surf, font):
        if self.life<=0: return
        a=clamp(self.life/self.max_life*1.5,0,1); ts=font.render(self.text,True,self.color); ts.set_alpha(int(255*a))
        os=font.render(self.text,True,(0,0,0)); os.set_alpha(int(180*a))
        if self.scale>0.1:
            w=max(1,int(ts.get_width()*self.scale)); h=max(1,int(ts.get_height()*self.scale))
            ts=pygame.transform.smoothscale(ts,(w,h)); os=pygame.transform.smoothscale(os,(w,h))
        tr=ts.get_rect(center=(self.x,self.y))
        for dx,dy in [(-1,0),(1,0),(0,-1),(0,1)]: surf.blit(os,tr.move(dx,dy))
        surf.blit(ts,tr)

class Button:
    def __init__(self, rect, text, callback=None, color=None, text_color=None, font_size=22):
        self.rect=pygame.Rect(rect); self.text=text; self.callback=callback; self.color=color or COL_PANEL_LIGHT
        self.text_color=text_color or COL_TEXT; self.font_size=font_size; self.hover_t=0; self.hovered=False
        self.press_anim=0; self.disabled=False; self.glow_t=0
    def update(self, dt, mp):
        wh=self.hovered; self.hovered=self.rect.collidepoint(mp) and not self.disabled
        t=1.0 if self.hovered else 0.0; self.hover_t+=(t-self.hover_t)*min(1,dt*12)
        self.press_anim=max(0,self.press_anim-dt*5); self.glow_t=max(0,self.glow_t-dt*2)
        return "hover" if (self.hovered and not wh) else None
    def trigger_press(self):
        if self.disabled: return
        self.press_anim=1.0; self.glow_t=1.0
        if self.callback: self.callback()
    def draw(self, surf, font):
        r=self.rect.move(0,int(self.press_anim*2))
        if self.glow_t>0:
            for i in range(3):
                gr=r.inflate(i*4+4,i*4+4); a=int(60*self.glow_t*(1-i/3))
                gs=pygame.Surface((gr.w,gr.h),pygame.SRCALPHA); pygame.draw.rect(gs,(*COL_GOLD,a),gs.get_rect(),border_radius=12); surf.blit(gs,gr.topleft)
        sh=pygame.Surface((r.w,r.h),pygame.SRCALPHA); pygame.draw.rect(sh,(0,0,0,100),sh.get_rect(),border_radius=10); surf.blit(sh,r.move(0,5).topleft)
        bg=lerp_color(self.color,COL_BORDER_BR,self.hover_t*0.4) if not self.disabled else COL_PANEL_DARK
        pygame.draw.rect(surf,bg,r,border_radius=10)
        bc=lerp_color(COL_BORDER,COL_GOLD_BR,self.hover_t) if not self.disabled else COL_BORDER
        pygame.draw.rect(surf,bc,r,width=2,border_radius=10)
        tc=self.text_color if not self.disabled else COL_TEXT_DIM
        ts=font.render(self.text,True,tc); surf.blit(ts,ts.get_rect(center=r.center))

class Game:
    def __init__(self, screen, sound):
        self.screen=screen; self.sound=sound; self.state=GameState.MENU; self.government=None; self.policy=None
        self.difficulty="NORMAL"; self.turn=1; self.fps=0
        self.resources={"treasury":50,"influence":50,"happiness":60,"stability":60,"military":50}
        self.target_resources=self.resources.copy(); self.display_resources=self.resources.copy()
        self.resource_pulse={k:0 for k in RES_ORDER}; self.rival_power=10; self.target_rival_power=10; self.display_rival_power=10
        self.rival_name=""; self.foreign_relations=[50,50,50]; self.target_foreign=[50,50,50]; self.display_foreign=[50,50,50]; self.foreign_pulse=[0,0,0]
        self.population=5.0; self.target_population=5.0; self.display_population=5.0; self.pop_pulse=0
        self.queued_event_id=None; self.weather='clear'; self.state_tier="STABLE"; self.current_event=None; self.last_event=None
        self.log=[]; self.full_history=[]; self.history={k:[v] for k,v in self.resources.items()}; self.history["rival"]=[self.rival_power]
        self.particles=[]; self.weather_particles=[]; self.floating_texts=[]; self.tweens=[]; self.modifiers=[]
        self.research_options=[]; self.project_options=[]; self.trade_options=[]; self.permanent_drifts=[]
        self.prophecy_options=[]; self.active_prophecy=None; self.prophecy_end_turn=0
        self.stats={"gold_gained":0,"soldiers_lost":0,"crises_survived":0,"decisions":0,"peak_pop":5.0,"prophecies_fulfilled":0,"prophecies_failed":0,"decrees_issued":0,"boons_used":0}
        self.popup_t=0; self.shake_amount=0; self.shake_time=0; self.hit_stop=0; self.flash_timer=0; self.flash_color=COL_GOLD
        self.vignette=self._create_vignette(); self.reduced_motion=False; self.show_debug=False; self.show_graph=False; self.show_history=False; self.show_stats=False
        self.time_scale=1.0; self.turn_phase=TurnPhase.INTRO; self.phase_timer=0; self.event_card_t=0; self.selected_choice_idx=None
        self.nudged=False; self.check_result=None; self.effect_display_timer=0; self.cause_of_death=""
        self.menu_t=0; self.gov_select_t=0; self.policy_select_t=0; self.game_over_t=0; self.gov_select_index=0; self.policy_select_index=0
        self.choice_buttons=[]; self.decree_buttons=[]; self.research_buttons=[]; self.project_buttons=[]; self.trade_buttons=[]; self.court_buttons=[]; self.boon_buttons=[]; self.prophecy_buttons=[]
        self.menu_buttons=[]; self.gov_cards=[]; self.policy_cards=[]; self.difficulty_buttons=[]; self.game_over_buttons=[]
        self.title_anim=0; self.achieved_milestones=set(); self.milestone_popup=None; self.milestone_popup_t=0
        self.hovered_resource=None; self.crises_survived=0; self.choices_made=0
        self.ruler_name=""; self.ruler_title=""; self.dynasty_name=""; self.advisor_advice={}; self.advisor_reactions={}
        self.decree_used=False; self.court=list(DEFAULT_COURT); self.boons_used={a["name"]:False for a in self.court}
        self.court_role_to_fill=-1; self.court_candidates=[]
        self.pending_schedule=False # Used to delay scheduling after prophecy resolution
        self.bg_dots=[[random.randint(0,WIDTH),random.randint(0,HEIGHT),random.uniform(0.3,1.0)] for _ in range(60)]
        self.bg_shapes=[{'x':random.randint(0,WIDTH),'y':random.randint(0,HEIGHT),'r':random.uniform(100,300),'color':random.choice([COL_PANEL,COL_BG_GRAD]),'speed':random.uniform(5,15)} for _ in range(5)]
        self._setup_menu(); self._setup_gov_select(); self._setup_policy_select(); self._setup_difficulty_buttons(); self._setup_game_over(); self._setup_decree_buttons()

    def _create_vignette(self):
        surf=pygame.Surface((WIDTH,HEIGHT),pygame.SRCALPHA); cx,cy=WIDTH//2,HEIGHT//2; md=math.hypot(cx,cy)
        for y in range(0,HEIGHT,4):
            for x in range(0,WIDTH,4):
                d=math.hypot(x-cx,y-cy); a=int(120*(d/md)**2); pygame.draw.rect(surf,(0,0,0,a),(x,y,4,4))
        return surf

    def _setup_menu(self):
        self.menu_buttons=[Button((WIDTH//2-120,470,240,60),"BEGIN REIGN",callback=self.start_gov_select,font_size=24),
                           Button((WIDTH//2-100,550,200,45),"ABANDON",callback=self.quit_game,font_size=18)]
    def _setup_gov_select(self):
        self.gov_cards=[]; cw,ch=360,220; gx,gy=30,30; sx=(WIDTH-(cw*3+gx*2))//2
        for i,g in enumerate(GOVERNMENTS):
            r,c=i//3,i%3; x=sx+c*(cw+gx); y=180+r*(ch+gy)
            self.gov_cards.append({"rect":pygame.Rect(x,y,cw,ch),"gov":g,"hover_t":0})
    def _setup_policy_select(self):
        self.policy_cards=[]; cw,ch=260,320; g=30; sx=(WIDTH-(cw*4+g*3))//2
        for i,p in enumerate(POLICIES):
            x=sx+i*(cw+g); self.policy_cards.append({"rect":pygame.Rect(x,220,cw,ch),"policy":p,"hover_t":0})
    def _setup_difficulty_buttons(self):
        self.difficulty_buttons=[{"rect":pygame.Rect(WIDTH//2-180+i*120,680,110,50),"diff":d} for i,d in enumerate(["STORY","NORMAL","IRONMAN"])]
    def _setup_game_over(self):
        self.game_over_buttons=[Button((WIDTH//2-240,HEIGHT-90,220,55),"NEW REIGN",callback=self.restart,font_size=22),
                                Button((WIDTH//2+20,HEIGHT-90,220,55),"MAIN MENU",callback=self.to_menu,font_size=22)]
    def _setup_decree_buttons(self):
        self.decree_buttons=[]; y,bw,bh,g=145,125,35,10; sx=240+(800-(bw*7+g*6))//2
        for i,d in enumerate(DECREES):
            x=sx+i*(bw+g); btn=Button((x,y,bw,bh),d["name"],callback=lambda dec=d:self.apply_decree(dec),font_size=12); self.decree_buttons.append(btn)
    def _setup_boon_buttons(self):
        self.boon_buttons=[]
        for i in range(3): btn=Button((40,170+i*160+125,120,25),"USE BOON",callback=lambda idx=i:self.use_boon(idx),font_size=12); self.boon_buttons.append(btn)

    def quit_game(self): pygame.event.post(pygame.event.Event(pygame.QUIT))
    def to_menu(self): self.state=GameState.MENU; self.menu_t=0; self.sound.play('whoosh')
    def start_gov_select(self): self.state=GameState.GOV_SELECT; self.gov_select_t=0; self.gov_select_index=0; self.sound.play('whoosh')
    def start_policy_select(self): self.state=GameState.POLICY_SELECT; self.policy_select_t=0; self.policy_select_index=0; self.sound.play('whoosh')

    def restart(self):
        self.government=None; self.policy=None; self.turn=1
        self.resources={"treasury":50,"influence":50,"happiness":60,"stability":60,"military":50}
        self.target_resources=self.resources.copy(); self.display_resources=self.resources.copy()
        self.resource_pulse={k:0 for k in RES_ORDER}; self.rival_power=10; self.target_rival_power=10; self.display_rival_power=10
        self.foreign_relations=[50,50,50]; self.target_foreign=[50,50,50]; self.display_foreign=[50,50,50]; self.foreign_pulse=[0,0,0]
        self.population=5.0; self.target_population=5.0; self.display_population=5.0; self.pop_pulse=0
        self.queued_event_id=None; self.current_event=None; self.last_event=None; self.log=[]
        self.full_history=[]; self.history={k:[v] for k,v in self.resources.items()}; self.history["rival"]=[self.rival_power]
        self.particles=[]; self.weather_particles=[]; self.floating_texts=[]; self.tweens=[]; self.modifiers=[]
        self.permanent_drifts=[]; self.research_options=[]; self.project_options=[]; self.trade_options=[]
        self.prophecy_options=[]; self.active_prophecy=None; self.prophecy_end_turn=0
        self.stats={"gold_gained":0,"soldiers_lost":0,"crises_survived":0,"decisions":0,"peak_pop":5.0,"prophecies_fulfilled":0,"prophecies_failed":0,"decrees_issued":0,"boons_used":0}
        self.court=list(DEFAULT_COURT); self.boons_used={a["name"]:False for a in self.court}
        self.court_role_to_fill=-1; self.court_candidates=[]
        self.cause_of_death=""; self.achieved_milestones=set(); self.milestone_popup=None
        self.crises_survived=0; self.choices_made=0; self.pending_schedule=False
        self.state=GameState.GOV_SELECT; self.gov_select_t=0; self.gov_select_index=0; self.sound.play('whoosh')

    def select_government(self, gov): self.government=gov; self.start_policy_select()
    def select_policy(self, policy): self.policy=policy; self.start_game()
    def start_game(self):
        self.state=GameState.PLAYING; self.turn=1
        self.resources=self.government.start.copy(); self.target_resources=self.resources.copy(); self.display_resources=self.resources.copy()
        self.history={k:[v] for k,v in self.resources.items()}; self.history["rival"]=[self.rival_power]
        self.ruler_name=random.choice(RULER_NAMES); self.ruler_title=GOV_TITLES[self.government.type]
        self.dynasty_name=random.choice(DYNASTY_NAMES); self.rival_name=random.choice(RIVAL_NAMES)
        self.log=[f"Year 1: {self.ruler_title} {self.ruler_name} of House {self.dynasty_name} begins their reign."]
        self.full_history=[self.log[0]]
        self._setup_boon_buttons(); self.update_weather(); self.next_event(); self.sound.play('whoosh')

    def update_weather(self):
        s=self.turn%4
        if s==0: self.weather='clear'
        elif s==1: self.weather='clear'
        elif s==2: self.weather='rain'
        elif s==3: self.weather='snow'
        if self.resources['happiness']<20 or self.resources['stability']<20 or self.resources['military']>85: self.weather='ash'
        elif all(v>=80 for v in self.resources.values()): self.weather='golden'
        self.sound.update_weather_sound(self.weather)

    def next_event(self):
        self.decree_used=False; self.advisor_reactions={}; self.update_weather()
        if self.queued_event_id:
            self.current_event=next((e for e in EVENTS if e.event_id==self.queued_event_id),None); self.queued_event_id=None
            if self.current_event:
                self.last_event=self.current_event; self.turn_phase=TurnPhase.INTRO; self.phase_timer=0; self.event_card_t=0
                self.selected_choice_idx=None; self.nudged=False; self.check_result=None
                if self.current_event.is_crisis: self.sound.play('crisis',0.4); self.flash_timer=0.4; self.flash_color=COL_RED
                else: self.sound.play('tick')
                self._setup_choice_buttons(); self._generate_advice(); return
        ac=[e for e in EVENTS if e.condition and e.condition(self) and e!=self.last_event and not e.event_id]
        if ac:
            self.current_event=ac[0]; self.last_event=self.current_event; self.turn_phase=TurnPhase.INTRO; self.phase_timer=0; self.event_card_t=0
            self.selected_choice_idx=None; self.nudged=False; self.check_result=None
            if self.current_event.is_crisis: self.sound.play('crisis',0.4); self.flash_timer=0.4; self.flash_color=COL_RED
            else: self.sound.play('tick')
            self._setup_choice_buttons(); self._generate_advice(); return
        av=[]
        for e in EVENTS:
            if e==self.last_event: continue
            if e.condition: continue
            if e.event_id: continue
            if e.gov_types is not None and self.government.type not in e.gov_types: continue
            av.append(e)
        if self.resources["stability"]<25 and random.random()<0.35:
            ce=[e for e in av if e.is_crisis]
            if ce:
                self.current_event=random.choice(ce); self.last_event=self.current_event; self.turn_phase=TurnPhase.INTRO; self.phase_timer=0; self.event_card_t=0
                self.selected_choice_idx=None; self.nudged=False; self.check_result=None
                self.sound.play('crisis',0.4); self.flash_timer=0.4; self.flash_color=COL_RED
                self._setup_choice_buttons(); self._generate_advice(); return
        if self.rival_power>60 and random.random()<0.30:
            re=[e for e in av if any("rival" in str(c.effects) for c in e.choices)]
            if re:
                self.current_event=random.choice(re); self.last_event=self.current_event; self.turn_phase=TurnPhase.INTRO; self.phase_timer=0; self.event_card_t=0
                self.selected_choice_idx=None; self.nudged=False; self.check_result=None
                self.sound.play('crisis',0.3); self._setup_choice_buttons(); self._generate_advice(); return
        self.current_event=random.choice(av); self.last_event=self.current_event; self.turn_phase=TurnPhase.INTRO; self.phase_timer=0; self.event_card_t=0
        self.selected_choice_idx=None; self.nudged=False; self.check_result=None
        self.sound.play('tick'); self._setup_choice_buttons(); self._generate_advice()

    def _generate_advice(self):
        self.advisor_advice={}
        if not self.current_event: return
        for a in self.court:
            bi,bs=-1,-999
            for i,c in enumerate(self.current_event.choices):
                s=0
                for st in a["drift"].keys():
                    if st in c.effects: s+=c.effects[st]
                if a["drift"]: s+=c.effects.get(list(a["drift"].keys())[0],0)*0.5
                if s>bs: bs=s; bi=i
            if self.current_event.is_crisis: m=f"Act fast! Option {bi+1}!"
            elif bs>15: m=f"Choice {bi+1} is vital!"
            elif bs>0: m=f"I suggest option {bi+1}."
            elif bs>-15: m=f"Option {bi+1} is safest."
            else: m=f"A bleak choice. {bi+1}?"
            self.advisor_advice[a["name"]]=(bi,m)

    def _setup_choice_buttons(self):
        self.choice_buttons=[]; bw,bx=760,240+(800-760)//2
        for i,c in enumerate(self.current_event.choices):
            btn=Button((bx,340+i*75,bw,65),c.text,callback=lambda c=c,idx=i:self.apply_choice(c,idx),font_size=20); self.choice_buttons.append(btn)

    def add_tween(self, obj, attr, start, end, duration, easing_func=ease_out_cubic):
        # Remove existing tweens for the same object and attribute to prevent conflicts
        self.tweens = [t for t in self.tweens if not (t.obj is obj and t.attr == attr)]
        self.tweens.append(Tween(obj, attr, start, end, duration, easing_func))

    def _trigger_res_fb(self, res, delta, dm=1.0):
        if delta==0: return
        if res=="rival":
            self.target_rival_power=clamp(self.target_rival_power+delta,0,100)
            start_val = self.display_rival_power
            self.add_tween(self,"display_rival_power",start_val,self.target_rival_power,0.5,ease_out_cubic)
            bx,by=WIDTH-300,120; col=COL_ORANGE if delta<0 else COL_RED_BR
            for _ in range(min(20,abs(delta)+5)):
                a=random.uniform(-math.pi,0); sp=random.uniform(80,240)
                self.particles.append(Particle(bx+random.uniform(-30,30),by+random.uniform(-5,5),math.cos(a)*sp,math.sin(a)*sp-50,random.uniform(0.5,1.0),col,random.uniform(2,4),gravity=320))
            s="+" if delta>0 else ""; self.floating_texts.append(FloatingText(bx,by-20,f"{s}{delta}",col,life=1.2,vy=-80,size=24))
            self.sound.play('positive' if delta<0 else 'negative',0.2); return
        ad=int(delta*dm) if delta<0 else delta
        old=self.target_resources[res]; new=clamp(old+ad,0,100); self.target_resources[res]=new
        start_val = self.display_resources[res]
        self.add_tween(self.display_resources,res,start_val,new,0.5,ease_out_cubic); self.resource_pulse[res]=1.0
        bx,by=self._res_bar_x(res),95; col=COL_GREEN_BR if ad>0 else COL_RED_BR
        for _ in range(min(20,abs(ad)+5)):
            a=random.uniform(-math.pi,0); sp=random.uniform(80,240)
            self.particles.append(Particle(bx+random.uniform(-30,30),by+random.uniform(-5,5),math.cos(a)*sp,math.sin(a)*sp-50,random.uniform(0.5,1.0),col,random.uniform(2,4),gravity=320))
        s="+" if ad>0 else ""; self.floating_texts.append(FloatingText(bx,by-20,f"{s}{ad}",col,life=1.2,vy=-80,size=24))
        self.sound.play('positive' if ad>0 else 'negative',0.2)
        # Stats tracking
        if res == "treasury" and ad > 0: self.stats["gold_gained"] += ad
        if res == "military" and ad < 0: self.stats["soldiers_lost"] += abs(ad)

    def _trigger_fp_fb(self, pi, delta):
        if delta==0: return
        old=self.target_foreign[pi]; new=clamp(old+delta,0,100); self.target_foreign[pi]=new
        start_val = self.display_foreign[pi]
        self.add_tween(self.display_foreign, str(pi), start_val, new, 0.5, ease_out_cubic); self.foreign_pulse[pi]=1.0
        fp=FOREIGN_POWERS[pi]; bx,by=450+pi*170,75; col=COL_GREEN_BR if delta>0 else COL_RED_BR
        for _ in range(min(15,abs(delta)+3)):
            a=random.uniform(-math.pi,0); sp=random.uniform(60,180)
            self.particles.append(Particle(bx+random.uniform(-40,40),by+random.uniform(-5,5),math.cos(a)*sp,math.sin(a)*sp-30,random.uniform(0.5,1.0),col,random.uniform(2,4),gravity=280))
        s="+" if delta>0 else ""; self.floating_texts.append(FloatingText(bx,by-15,f"{s}{delta} {fp['name'][:3]}",col,life=1.0,vy=-60,size=18))
        self.sound.play('diplomacy',0.3)

    def apply_decree(self, d):
        if self.decree_used or self.turn_phase!=TurnPhase.ACTIVE: return
        if self.target_resources["treasury"]<d["cost"]: return
        self.decree_used=True; self.sound.play('click'); self.stats["decrees_issued"] += 1
        for r,dl in d["effects"].items(): self._trigger_res_fb(r,dl)
        for md in d.get("modifiers",[]):
            self.modifiers.append(Modifier(name=md["name"],description=md["desc"],duration=md["duration"],max_duration=md["duration"],drift=md["drift"],color=md["color"],pulse_t=1.0))
            self.sound.play('policy',0.5)
            for _ in range(15):
                a=random.uniform(0,math.pi*2); sp=random.uniform(50,150)
                self.particles.append(Particle(1060+100,250,math.cos(a)*sp,math.sin(a)*sp,random.uniform(0.5,1.0),md["color"],random.uniform(2,4),gravity=100,shape='star'))
        if "foreign" in d:
            for fn,dl in d["foreign"].items():
                if fn=="rand":
                    i=random.randint(0,2); self._trigger_fp_fb(i,dl)
                else:
                    i=next(i for i,fp in enumerate(FOREIGN_POWERS) if fp["name"].lower()==fn); self._trigger_fp_fb(i,dl)
        self.log.insert(0,f"Year {self.turn}: Royal Decree: {d['name']}")
        self.full_history.append(self.log[0])
        if len(self.log)>5: self.log.pop()

    def use_boon(self, ai):
        if self.turn_phase!=TurnPhase.ACTIVE: return
        a=self.court[ai]
        if self.boons_used.get(a["name"]): return
        self.boons_used[a["name"]]=True; self.sound.play('boon'); self.flash_timer=0.5; self.flash_color=a["color"]
        self.stats["boons_used"] += 1
        bn=a.get("boon","")
        if bn=="MARTIAL LAW": self._trigger_res_fb("stability",15); self._trigger_res_fb("happiness",-10); self._trigger_res_fb("rival",-10)
        elif bn=="DIPLOMATIC ENVOY":
            for i in range(3): self._trigger_fp_fb(i,15)
            self._trigger_res_fb("influence",5)
        elif bn=="EMERGENCY FUNDS": self._trigger_res_fb("treasury",25); self._trigger_res_fb("influence",-5)
        self.log.insert(0,f"Year {self.turn}: {a['name']} used {bn}!")
        self.full_history.append(self.log[0])
        if len(self.log)>5: self.log.pop()

    def apply_choice(self, c, idx, nudged=False):
        if self.turn_phase!=TurnPhase.ACTIVE: return
        self.selected_choice_idx=idx; self.nudged=nudged; self.effect_display_timer=1.8; self.turn_phase=TurnPhase.EFFECTS; self.phase_timer=0
        self.sound.play('click'); self.choices_made+=1; self.stats["decisions"]+=1
        if self.current_event.is_crisis: self.crises_survived+=1; self.stats["crises_survived"]+=1
        self.queued_event_id=c.queue; self.advisor_reactions={}
        for a in self.court:
            bi,_=self.advisor_advice.get(a["name"],(-1,"")); s=0
            for st in a["drift"].keys():
                if st in c.effects: s+=c.effects[st]
            if a["drift"]: s+=c.effects.get(list(a["drift"].keys())[0],0)*0.5
            if idx==bi and s>0: r="A wise move, my liege!"
            elif s>15: r="An acceptable outcome."
            elif s>-10: r="A grim necessity."
            elif s<-20: r="I strongly object!"
            else: r="We must press on."
            self.advisor_reactions[a["name"]]=r
        dm=0.7 if self.difficulty=="STORY" else (1.4 if self.difficulty=="IRONMAN" else 1.0)
        eta=c.effects.copy(); self.check_result=None
        if c.check:
            st=c.check["stat"]; sv=self.target_resources.get(st,0); ch=clamp(sv,5,95)
            if random.randint(1,100)<=ch:
                self.check_result="SUCCESS"
                for k,v in c.check["success"].items(): eta[k]=eta.get(k,0)+v
            else:
                self.check_result="FAILURE"
                for k,v in c.check["failure"].items(): eta[k]=eta.get(k,0)+v
        if nudged:
            self.sound.play('nudge',0.6)
            self.target_resources["influence"]=clamp(self.target_resources["influence"]-10,0,100)
            start_val = self.display_resources["influence"]
            self.add_tween(self.display_resources,"influence",start_val,self.target_resources["influence"],0.5,ease_out_cubic)
            self.resource_pulse["influence"]=1.0
            for r,v in eta.items():
                if v>0: eta[r]=v+5
                elif v<0: eta[r]=v+5
            bx=self._res_bar_x("influence"); self.floating_texts.append(FloatingText(bx,80,"-10 NUDGE",COL_PURPLE,life=1.2,vy=-80,size=20))
            for _ in range(15):
                a=random.uniform(-math.pi,0); sp=random.uniform(100,200)
                self.particles.append(Particle(bx,90,math.cos(a)*sp,math.sin(a)*sp-30,random.uniform(0.5,1.0),COL_PURPLE,random.uniform(2,4),gravity=200,shape='star'))
        for r,dl in eta.items(): self._trigger_res_fb(r,dl,dm)
        for fn,dl in c.foreign.items():
            i=next(i for i,fp in enumerate(FOREIGN_POWERS) if fp["name"].lower()==fn); self._trigger_fp_fb(i,dl)
        for md in c.modifiers:
            self.modifiers.append(Modifier(name=md["name"],description=md["desc"],duration=md["duration"],max_duration=md["duration"],drift=md["drift"],color=md["color"],pulse_t=1.0))
            self.sound.play('policy',0.5)
            for _ in range(15):
                a=random.uniform(0,math.pi*2); sp=random.uniform(50,150)
                self.particles.append(Particle(1060+100,250,math.cos(a)*sp,math.sin(a)*sp,random.uniform(0.5,1.0),md["color"],random.uniform(2,4),gravity=100,shape='star'))
        tn=sum(min(0,int(v*dm) if v<0 else v) for k,v in eta.items() if k!="rival")
        if tn<-20: self.shake_amount=min(8,max(self.shake_amount,abs(tn)*0.25)); self.shake_time=0.4; self.hit_stop=0.08
        log_msg=f"Year {self.turn}: {self.current_event.title} → {c.text}"+(" (Nudged)" if nudged else "")
        self.log.insert(0,log_msg)
        self.full_history.append(log_msg)
        if len(self.log)>5: self.log.pop()

    def _res_bar_x(self, res):
        i=RES_ORDER.index(res); bw,g=140,15; tw=bw*5+g*4; sx=240+(800-tw)//2; return sx+i*(bw+g)+bw//2

    def check_milestones(self):
        ms=[("decade","DECADE OF RULE","Survived 10 years.",lambda g:g.turn>=11,COL_GOLD_BR),
            ("golden","GOLDEN TREASURY","Treasury 90+.",lambda g:g.resources["treasury"]>=90,COL_GOLD),
            ("beloved","BELOVED LEADER","Happiness 90+.",lambda g:g.resources["happiness"]>=90,COL_GREEN_BR),
            ("iron","IRON FIST","Military 90+.",lambda g:g.resources["military"]>=90,COL_RED_BR),
            ("diplomat","DIPLOMATIC MASTER","Influence 90+.",lambda g:g.resources["influence"]>=90,COL_PURPLE),
            ("pillar","PILLAR OF ORDER","Stability 90+.",lambda g:g.resources["stability"]>=90,COL_BLUE),
            ("survivor","THE SURVIVOR","Reached year 20.",lambda g:g.turn>=21,COL_TEAL),
            ("allied","GRAND ALLIANCE","All 3 powers 70+.",lambda g:all(g.foreign_relations[i]>=70 for i in range(3)),COL_CYAN),
            ("populous","TEEMING REALM","Population 10M+.",lambda g:g.population>=10,COL_PINK)]
        for mid,ti,de,co,cl in ms:
            if mid not in self.achieved_milestones and co(self):
                self.achieved_milestones.add(mid); self.milestone_popup={"title":ti,"desc":de,"color":cl}; self.milestone_popup_t=0
                self.sound.play('milestone',0.5); self.flash_timer=0.5; self.flash_color=cl
                for _ in range(30):
                    a=random.uniform(0,math.pi*2); sp=random.uniform(100,300)
                    self.particles.append(Particle(WIDTH//2,300,math.cos(a)*sp,math.sin(a)*sp-50,random.uniform(0.8,1.5),cl,random.uniform(3,5),gravity=200,shape='star'))

    def check_game_over(self):
        for r,v in self.resources.items():
            if v<=0:
                cd={"treasury":"BANKRUPTCY — Creditors circle like vultures.","influence":"IRRELEVANCE — You are a puppet.","happiness":"REVOLUTION — The people have risen.","stability":"COLLAPSE — The nation shatters.","military":"INVASION — Foreign powers carve your realm."}
                self.cause_of_death=cd[r]; return True
        if self.rival_power>=100:
            if self.difficulty == "IRONMAN":
                self.cause_of_death = "USURPATION — Your rivals have overthrown you."
                return True
            self.rival_power=60; self.target_rival_power=60; self.display_rival_power=60
            self.modifiers.append(Modifier(name="CIVIL WAR",description="Rivals have taken up arms!",duration=5,max_duration=5,drift={"stability":-5,"military":-3,"rival":5},color=COL_RED,pulse_t=1.0))
            self.shake_amount=8; self.shake_time=0.4; self.flash_timer=0.6; self.flash_color=COL_RED; self.sound.play('war',0.8)
            self.log.insert(0,"CRISIS: Civil War erupts! Rivals storm the capital!")
            self.full_history.append(self.log[0])
            if len(self.log)>5: self.log.pop(); return False
        return False

    def trigger_research(self):
        self.research_options=random.sample(RESEARCH_UPGRADES,3); self.research_buttons=[]
        bw,bh,g=220,260,20; sx=(WIDTH-(bw*3+g*2))//2
        for i,r in enumerate(self.research_options):
            x=sx+i*(bw+g); btn=Button((x,HEIGHT//2-bh//2,bw,bh),"ADOPT",callback=lambda r=r:self.apply_research(r),font_size=18)
            self.research_buttons.append({"btn":btn,"res":r,"hover_t":0})
    def apply_research(self, r):
        self.permanent_drifts.append(r); self.research_options=[]; self.sound.play('research'); self.flash_timer=0.4; self.flash_color=r["color"]
        for _ in range(20):
            a=random.uniform(0,math.pi*2); sp=random.uniform(100,200)
            self.particles.append(Particle(WIDTH//2,HEIGHT//2,math.cos(a)*sp,math.sin(a)*sp,random.uniform(0.8,1.2),r["color"],random.uniform(3,5),gravity=50,shape='star'))
        log_msg=f"Year {self.turn}: Research Adopted: {r['name']}"
        self.log.insert(0,log_msg); self.full_history.append(log_msg)
        if len(self.log)>5: self.log.pop(); self.turn_phase=TurnPhase.TRANSITION; self.phase_timer=0

    def trigger_project(self):
        self.project_options=random.sample(PROJECTS,3); self.project_buttons=[]
        bw,bh,g=240,280,20; sx=(WIDTH-(bw*3+g*2))//2
        for i,p in enumerate(self.project_options):
            x=sx+i*(bw+g); btn=Button((x,HEIGHT//2-bh//2,bw,bh),"BUILD (25T)",callback=lambda p=p:self.apply_project(p),font_size=18)
            self.project_buttons.append({"btn":btn,"proj":p,"hover_t":0})
    def apply_project(self, p):
        if self.target_resources["treasury"]<25: return
        self._trigger_res_fb("treasury",-25); self.permanent_drifts.append(p); self.project_options=[]
        self.sound.play('policy'); self.flash_timer=0.4; self.flash_color=p["color"]
        for _ in range(30):
            a=random.uniform(0,math.pi*2); sp=random.uniform(100,200)
            self.particles.append(Particle(WIDTH//2,HEIGHT//2,math.cos(a)*sp,math.sin(a)*sp,random.uniform(0.8,1.2),p["color"],random.uniform(4,6),gravity=80,shape='star'))
        log_msg=f"Year {self.turn}: Project Completed: {p['name']}"
        self.log.insert(0,log_msg); self.full_history.append(log_msg)
        if len(self.log)>5: self.log.pop(); self.turn_phase=TurnPhase.TRANSITION; self.phase_timer=0

    def trigger_trade(self):
        self.trade_options=random.sample(TRADE_ROUTES,3); self.trade_buttons=[]
        bw,bh,g=240,280,20; sx=(WIDTH-(bw*3+g*2))//2
        for i,t in enumerate(self.trade_options):
            x=sx+i*(bw+g); btn=Button((x,HEIGHT//2-bh//2,bw,bh),"ESTABLISH (20T)",callback=lambda t=t:self.apply_trade(t),font_size=16)
            self.trade_buttons.append({"btn":btn,"trade":t,"hover_t":0})
    def apply_trade(self, t):
        if self.target_resources["treasury"]<20: return
        self._trigger_res_fb("treasury",-20); self.permanent_drifts.append(t); self.trade_options=[]
        self.sound.play('policy'); self.flash_timer=0.4; self.flash_color=t["color"]
        for _ in range(25):
            a=random.uniform(0,math.pi*2); sp=random.uniform(100,200)
            self.particles.append(Particle(WIDTH//2,HEIGHT//2,math.cos(a)*sp,math.sin(a)*sp,random.uniform(0.8,1.2),t["color"],random.uniform(3,5),gravity=60,shape='star'))
        log_msg=f"Year {self.turn}: Trade Route: {t['name']}"
        self.log.insert(0,log_msg); self.full_history.append(log_msg)
        if len(self.log)>5: self.log.pop(); self.turn_phase=TurnPhase.TRANSITION; self.phase_timer=0

    def trigger_court(self, ri):
        self.court_role_to_fill=ri; rn=["MARSHAL","CHANCELLOR","STEWARD"][ri]
        self.court_candidates=random.sample([c for c in COURT_CANDIDATES if c["role"]==rn],3); self.court_buttons=[]
        bw,bh,g=220,280,20; sx=(WIDTH-(bw*3+g*2))//2
        for i,c in enumerate(self.court_candidates):
            x=sx+i*(bw+g); btn=Button((x,HEIGHT//2-bh//2,bw,bh),"APPOINT",callback=lambda c=c:self.apply_court(c),font_size=18)
            self.court_buttons.append({"btn":btn,"cand":c,"hover_t":0})
    def apply_court(self, c):
        on=self.court[self.court_role_to_fill]["name"]; self.court[self.court_role_to_fill]=c
        self.boons_used[c["name"]]=self.boons_used.get(on,False); self.sound.play('research'); self.flash_timer=0.4; self.flash_color=c["color"]
        for _ in range(20):
            a=random.uniform(0,math.pi*2); sp=random.uniform(100,200)
            self.particles.append(Particle(WIDTH//2,HEIGHT//2,math.cos(a)*sp,math.sin(a)*sp,random.uniform(0.8,1.2),c["color"],random.uniform(3,5),gravity=50,shape='star'))
        log_msg=f"Year {self.turn}: Appointed {c['name']} as {c['role']}."
        self.log.insert(0,log_msg); self.full_history.append(log_msg)
        if len(self.log)>5: self.log.pop(); self.court_role_to_fill=-1; self.court_candidates=[]; self.turn_phase=TurnPhase.TRANSITION; self.phase_timer=0

    def trigger_prophecy(self):
        self.prophecy_options=random.sample(PROPHECIES,3); self.prophecy_buttons=[]
        bw,bh,g=260,300,20; sx=(WIDTH-(bw*3+g*2))//2
        for i,p in enumerate(self.prophecy_options):
            x=sx+i*(bw+g); btn=Button((x,HEIGHT//2-bh//2,bw,bh),"ACCEPT",callback=lambda p=p:self.apply_prophecy(p),font_size=18)
            self.prophecy_buttons.append({"btn":btn,"prop":p,"hover_t":0})
        self.sound.play('prophecy')

    def apply_prophecy(self, p):
        self.active_prophecy=p; self.prophecy_end_turn=self.turn+5; self.prophecy_options=[]
        self.flash_timer=0.5; self.flash_color=p["color"]
        for _ in range(30):
            a=random.uniform(0,math.pi*2); sp=random.uniform(100,200)
            self.particles.append(Particle(WIDTH//2,HEIGHT//2,math.cos(a)*sp,math.sin(a)*sp,random.uniform(0.8,1.2),p["color"],random.uniform(4,6),gravity=0,shape='star'))
        log_msg=f"Year {self.turn}: Prophecy Accepted: {p['name']} ({p['desc']})"
        self.log.insert(0,log_msg); self.full_history.append(log_msg)
        if len(self.log)>5: self.log.pop(); self.turn_phase=TurnPhase.TRANSITION; self.phase_timer=0

    def resolve_prophecy(self):
        p=self.active_prophecy; cond_met=False
        if p["name"]=="GOLDEN PATH" and self.resources["treasury"]>60: cond_met=True
        elif p["name"]=="IRON FIST" and self.resources["stability"]>70: cond_met=True
        elif p["name"]=="PEOPLE'S VOICE" and self.resources["happiness"]>60: cond_met=True
        elif p["name"]=="CULTURAL ZENITH" and self.resources["influence"]>60: cond_met=True
        elif p["name"]=="SPARTAN WAY" and self.resources["military"]>70: cond_met=True

        res = p["reward"] if cond_met else p["penalty"]
        dm = 0.7 if self.difficulty=="STORY" else (1.4 if self.difficulty=="IRONMAN" else 1.0)
        for k,v in res.items():
            self._trigger_res_fb(k, v, dm)
            # Apply immediately so check_game_over is accurate
            if k != "rival":
                self.resources[k] = self.target_resources[k]
            else:
                self.rival_power = self.target_rival_power
        
        self.milestone_popup = {
            "title": f"PROPHECY {'FULFILLED' if cond_met else 'FAILED'}",
            "desc": p["name"],
            "color": COL_GREEN_BR if cond_met else COL_RED_BR
        }
        self.milestone_popup_t = 0
        self.sound.play('positive' if cond_met else 'negative', 0.8)
        self.flash_timer = 0.5
        self.flash_color = COL_GREEN_BR if cond_met else COL_RED_BR
        if not cond_met:
            self.shake_amount = 8
            self.shake_time = 0.4

        if cond_met:
            self.stats["prophecies_fulfilled"] += 1
        else:
            self.stats["prophecies_failed"] += 1

        log_msg = f"Year {self.turn}: Prophecy {p['name']} {'FULFILLED!' if cond_met else 'FAILED!'}"
        self.log.insert(0, log_msg); self.full_history.append(log_msg)
        if len(self.log) > 5: self.log.pop()
        
        self.active_prophecy = None

    def compute_rank(self, leg):
        if leg>=800: return ("S",COL_GOLD_BR)
        elif leg>=600: return ("A",COL_GREEN_BR)
        elif leg>=400: return ("B",COL_BLUE)
        elif leg>=250: return ("C",COL_PURPLE)
        elif leg>=100: return ("D",COL_ORANGE)
        else: return ("F",COL_RED_BR)

    def schedule_turn_event(self):
        if self.turn in [4, 9, 14, 19, 24, 29]: self.trigger_prophecy()
        elif (self.turn-1)%3==0 and self.turn<=24: self.trigger_trade()
        elif (self.turn-1)%4==0 and self.turn<=24: self.trigger_project()
        elif (self.turn-1)%5==0 and self.turn<=25: self.trigger_research()
        elif (self.turn-1)%6==0 and self.turn<=24:
            ri=((self.turn-1)//6-1)%3; self.trigger_court(ri)
        else: self.turn_phase=TurnPhase.TRANSITION; self.phase_timer=0; self.sound.play('transition')

    def next_turn(self):
        # Record history for the turn that just ended
        for k in RES_ORDER: self.history[k].append(self.resources[k])
        self.history["rival"].append(self.rival_power)
        
        self.turn+=1
        if self.turn>MAX_TURNS: self.state=GameState.VICTORY; self.game_over_t=0; self.sound.play('victory'); self.shake_amount=5; self.shake_time=0.4; return
        dm=0.5 if self.difficulty=="STORY" else (1.5 if self.difficulty=="IRONMAN" else 1.0)
        rm=0.6 if self.difficulty=="STORY" else (1.4 if self.difficulty=="IRONMAN" else 1.0)
        dr={"treasury":0,"influence":0,"happiness":0,"stability":0,"military":0,"rival":0}
        def apply_drift(d):
            for k,v in d.items():
                dr[k]=dr.get(k,0)+v
                if k=="rival": self.rival_power=clamp(self.rival_power+int(v*dm),0,100)
                else:
                    old_val = self.resources[k]
                    self.resources[k]=clamp(self.resources[k]+int(v*dm),0,100)
                    if k == "treasury" and v > 0:
                        self.stats["gold_gained"] += self.resources[k] - old_val
        apply_drift(self.government.drift); apply_drift(self.policy["drift"])
        for m in self.modifiers: apply_drift(m.drift)
        self.modifiers=[m for m in self.modifiers if m.duration>1]
        for m in self.modifiers: m.duration-=1
        self.modifiers=[m for m in self.modifiers if m.duration>0]
        for r in self.permanent_drifts: apply_drift(r["drift"])
        for a in self.court: apply_drift(a["drift"])
        rg=random.randint(3,6)-(self.resources["military"]//25); rg=int(rg*rm)
        self.rival_power=clamp(self.rival_power+max(1,rg),0,100); dr["rival"]+=max(1,rg)
        for i in range(3):
            dec=random.randint(1,3); self.foreign_relations[i]=clamp(self.foreign_relations[i]-dec,0,100)
            if self.foreign_relations[i]>=70:
                fp=FOREIGN_POWERS[i]; bk,bv=fp["bonus_key"],fp["bonus_val"]
                if bk=="rival": self.rival_power=clamp(self.rival_power-bv,0,100)
                else: self.resources[bk]=clamp(self.resources[bk]+bv,0,100)
            if self.foreign_relations[i]<=20 and random.random()<0.30:
                self.resources["military"]=clamp(self.resources["military"]-5,0,100); self.resources["stability"]=clamp(self.resources["stability"]-5,0,100)
                self.log.insert(0,f"Border raid from {FOREIGN_POWERS[i]['name']}!")
                self.full_history.append(self.log[0])
                if len(self.log)>5: self.log.pop()
                self.shake_amount=4; self.shake_time=0.4; self.flash_timer=0.3; self.flash_color=COL_RED
        pg=(self.resources["happiness"]-40)/200.0-(10 if self.weather=='ash' else 0)/100.0
        if self.resources["stability"]<20: pg-=0.5
        self.population=clamp(self.population+pg,0.5,20.0)
        if self.population > self.stats["peak_pop"]: self.stats["peak_pop"] = self.population
        pm=self.population/5.0
        if pm>1.0: self.resources["treasury"]=clamp(self.resources["treasury"]+int((pm-1)*3),0,100)
        elif pm<0.8:
            self.resources["treasury"]=clamp(self.resources["treasury"]-2,0,100); self.resources["military"]=clamp(self.resources["military"]-1,0,100)
        self.update_weather()
        ar=sum(self.resources.values())/5
        if ar>=75:
            self.state_tier="GOLDEN AGE"; self.resources['treasury']=clamp(self.resources['treasury']+2,0,100); self.resources['happiness']=clamp(self.resources['happiness']+2,0,100)
        elif ar<=25:
            self.state_tier="DARK AGE"; self.resources['stability']=clamp(self.resources['stability']-2,0,100); self.resources['happiness']=clamp(self.resources['happiness']-2,0,100)
        else: self.state_tier="STABLE"
        if self.weather=='snow': self.resources['treasury']=clamp(self.resources['treasury']-2,0,100)
        elif self.weather=='ash': self.resources['stability']=clamp(self.resources['stability']-2,0,100); self.resources['happiness']=clamp(self.resources['happiness']-1,0,100)
        elif self.weather=='golden': self.resources['treasury']=clamp(self.resources['treasury']+2,0,100); self.resources['happiness']=clamp(self.resources['happiness']+2,0,100)
        elif self.weather=='rain': self.resources['happiness']=clamp(self.resources['happiness']+1,0,100)
        self.target_resources=self.resources.copy(); self.display_resources=self.resources.copy()
        self.target_rival_power=self.rival_power; self.display_rival_power=self.rival_power
        self.target_foreign=self.foreign_relations.copy(); self.display_foreign=self.foreign_relations.copy()
        self.target_population=self.population; self.display_population=self.population
        s_str = " ".join([f"{k[:3].upper()}:{v:+d}" for k,v in dr.items() if v!=0])
        log_msg = f"Year {self.turn-1} End: {s_str}"
        self.log.insert(0, log_msg); self.full_history.append(log_msg)
        if len(self.log)>5: self.log.pop()
        
        self.check_milestones()
        if self.check_game_over():
            self.state=GameState.GAME_OVER; self.game_over_t=0; self.sound.play('game_over'); self.shake_amount=8; self.shake_time=0.4; self.hit_stop=0.15; return
        
        # Prophecy Resolution
        if self.active_prophecy and self.turn >= self.prophecy_end_turn:
            self.resolve_prophecy()
            if self.check_game_over():
                self.state=GameState.GAME_OVER; self.game_over_t=0; self.sound.play('game_over'); self.shake_amount=8; self.shake_time=0.4; self.hit_stop=0.15; return
            
            # Delay scheduling to show the resolution popup
            self.pending_schedule = True
            self.turn_phase = TurnPhase.TRANSITION
            self.phase_timer = 0
            self.sound.play('transition')
            return

        self.schedule_turn_event()

    def handle_event(self, e):
        if e.type==pygame.KEYDOWN:
            if e.key==pygame.K_ESCAPE:
                if self.state==GameState.PLAYING: self.state=GameState.PAUSED
                elif self.state==GameState.PAUSED: self.state=GameState.PLAYING
                elif self.state in (GameState.GAME_OVER,GameState.VICTORY,GameState.GOV_SELECT,GameState.POLICY_SELECT): self.to_menu()
            elif e.key==pygame.K_p:
                if self.state==GameState.PLAYING: self.state=GameState.PAUSED
                elif self.state==GameState.PAUSED: self.state=GameState.PLAYING
            elif e.key==pygame.K_m: 
                self.sound.muted=not self.sound.muted
                if self.sound.muted: self.sound.sounds['wind'].stop()
                else: self.sound.update_weather_sound(self.weather)
            elif e.key==pygame.K_r: self.reduced_motion=not self.reduced_motion
            elif e.key==pygame.K_F1: self.show_debug=not self.show_debug
            elif e.key==pygame.K_F2: self.time_scale=0.2 if self.time_scale>0.5 else 1.0
            elif e.key==pygame.K_g:
                if self.state==GameState.PLAYING: self.show_graph=not self.show_graph
            elif e.key==pygame.K_h:
                if self.state==GameState.PLAYING: self.show_history=not self.show_history
            elif e.key==pygame.K_j:
                if self.state==GameState.PLAYING: self.show_stats=not self.show_stats
            elif e.key==pygame.K_SPACE:
                if self.state==GameState.MENU: self.start_gov_select()
                elif self.state==GameState.GOV_SELECT: self.select_government(GOVERNMENTS[self.gov_select_index])
                elif self.state==GameState.POLICY_SELECT: self.select_policy(POLICIES[self.policy_select_index])
                elif self.state in (GameState.GAME_OVER,GameState.VICTORY): self.restart()
            elif e.key==pygame.K_RETURN:
                if self.state==GameState.MENU: self.start_gov_select()
                elif self.state==GameState.GOV_SELECT: self.select_government(GOVERNMENTS[self.gov_select_index])
                elif self.state==GameState.POLICY_SELECT: self.select_policy(POLICIES[self.policy_select_index])
            elif e.key in (pygame.K_UP,pygame.K_w):
                if self.state==GameState.GOV_SELECT: self.gov_select_index=(self.gov_select_index-3)%len(GOVERNMENTS); self.sound.play('hover')
                elif self.state==GameState.POLICY_SELECT: self.policy_select_index=(self.policy_select_index-1)%len(POLICIES); self.sound.play('hover')
            elif e.key in (pygame.K_DOWN,pygame.K_s):
                if self.state==GameState.GOV_SELECT: self.gov_select_index=(self.gov_select_index+3)%len(GOVERNMENTS); self.sound.play('hover')
                elif self.state==GameState.POLICY_SELECT: self.policy_select_index=(self.policy_select_index+1)%len(POLICIES); self.sound.play('hover')
            elif e.key in (pygame.K_LEFT,pygame.K_a):
                if self.state==GameState.GOV_SELECT: self.gov_select_index=(self.gov_select_index-1)%len(GOVERNMENTS); self.sound.play('hover')
                elif self.state==GameState.POLICY_SELECT: self.policy_select_index=(self.policy_select_index-1)%len(POLICIES); self.sound.play('hover')
            elif e.key in (pygame.K_RIGHT,pygame.K_d):
                if self.state==GameState.GOV_SELECT: self.gov_select_index=(self.gov_select_index+1)%len(GOVERNMENTS); self.sound.play('hover')
                elif self.state==GameState.POLICY_SELECT: self.policy_select_index=(self.policy_select_index+1)%len(POLICIES); self.sound.play('hover')
            elif e.key in (pygame.K_1,pygame.K_2,pygame.K_3):
                if self.state==GameState.PLAYING and self.turn_phase==TurnPhase.ACTIVE:
                    i=e.key-pygame.K_1
                    if i<len(self.choice_buttons): self.choice_buttons[i].trigger_press()
                elif self.state==GameState.PLAYING and self.research_options:
                    i=e.key-pygame.K_1
                    if i<len(self.research_buttons): self.research_buttons[i]["btn"].trigger_press()
                elif self.state==GameState.PLAYING and self.project_options:
                    i=e.key-pygame.K_1
                    if i<len(self.project_buttons): self.project_buttons[i]["btn"].trigger_press()
                elif self.state==GameState.PLAYING and self.trade_options:
                    i=e.key-pygame.K_1
                    if i<len(self.trade_buttons): self.trade_buttons[i]["btn"].trigger_press()
                elif self.state==GameState.PLAYING and self.court_candidates:
                    i=e.key-pygame.K_1
                    if i<len(self.court_buttons): self.court_buttons[i]["btn"].trigger_press()
                elif self.state==GameState.PLAYING and self.prophecy_options:
                    i=e.key-pygame.K_1
                    if i<len(self.prophecy_buttons): self.prophecy_buttons[i]["btn"].trigger_press()
            elif e.key in (pygame.K_4,pygame.K_5,pygame.K_6):
                if self.state==GameState.PLAYING and self.turn_phase==TurnPhase.ACTIVE and self.difficulty != "IRONMAN":
                    if self.target_resources["influence"]>=10:
                        i=e.key-pygame.K_4
                        if i<len(self.choice_buttons): self.apply_choice(self.current_event.choices[i],i,nudged=True)
            elif e.key in DECREE_KEYS:
                if self.state==GameState.PLAYING and self.turn_phase==TurnPhase.ACTIVE:
                    idx = DECREE_KEYS.index(e.key)
                    if idx < len(self.decree_buttons): self.decree_buttons[idx].trigger_press()
        if e.type==pygame.MOUSEBUTTONDOWN and e.button==1:
            mp=e.pos
            if self.state==GameState.MENU:
                for b in self.menu_buttons:
                    if b.rect.collidepoint(mp): b.trigger_press(); return
                for db in self.difficulty_buttons:
                    if db["rect"].collidepoint(mp): self.difficulty=db["diff"]; self.sound.play('click'); return
            elif self.state==GameState.GOV_SELECT:
                for c in self.gov_cards:
                    if c["rect"].collidepoint(mp): self.select_government(c["gov"]); return
            elif self.state==GameState.POLICY_SELECT:
                for c in self.policy_cards:
                    if c["rect"].collidepoint(mp): self.select_policy(c["policy"]); return
            elif self.state==GameState.PLAYING:
                if self.research_options:
                    for r in self.research_buttons:
                        if r["btn"].rect.collidepoint(mp): r["btn"].trigger_press(); return
                elif self.project_options:
                    for p in self.project_buttons:
                        if p["btn"].rect.collidepoint(mp): p["btn"].trigger_press(); return
                elif self.trade_options:
                    for t in self.trade_buttons:
                        if t["btn"].rect.collidepoint(mp): t["btn"].trigger_press(); return
                elif self.court_candidates:
                    for c in self.court_buttons:
                        if c["btn"].rect.collidepoint(mp): c["btn"].trigger_press(); return
                elif self.prophecy_options:
                    for p in self.prophecy_buttons:
                        if p["btn"].rect.collidepoint(mp): p["btn"].trigger_press(); return
                elif self.turn_phase==TurnPhase.ACTIVE:
                    for b in self.boon_buttons:
                        if b.rect.collidepoint(mp): b.trigger_press(); return
                    for b in self.decree_buttons:
                        if b.rect.collidepoint(mp): b.trigger_press(); return
                    for b in self.choice_buttons:
                        if b.rect.collidepoint(mp): b.trigger_press(); return
            elif self.state in (GameState.GAME_OVER,GameState.VICTORY):
                for b in self.game_over_buttons:
                    if b.rect.collidepoint(mp): b.trigger_press(); return

    def update(self, dt, fps=0):
        self.fps = fps
        for d in self.bg_dots:
            d[1]-=d[2]*18*dt
            if d[1]<0: d[1]=HEIGHT; d[0]=random.randint(0,WIDTH)
        for s in self.bg_shapes:
            s['y']-=s['speed']*dt
            if s['y']<-s['r']: s['y']=HEIGHT+s['r']; s['x']=random.randint(0,WIDTH)
        if self.hit_stop>0: self.hit_stop-=dt; return
        ds=dt*self.time_scale
        if self.flash_timer>0: self.flash_timer-=dt
        if self.weather=='rain' and len(self.weather_particles)<100:
            self.weather_particles.append(Particle(random.randint(0,WIDTH),-10,random.uniform(-50,-20),random.uniform(400,600),random.uniform(0.5,1.0),(100,150,200),random.uniform(2,4),gravity=100,shape='line',drag=1.0))
        elif self.weather=='snow' and len(self.weather_particles)<80:
            self.weather_particles.append(Particle(random.randint(0,WIDTH),-10,random.uniform(-20,20),random.uniform(50,100),random.uniform(2.0,4.0),(220,230,240),random.uniform(2,4),gravity=5,shape='circle',drag=0.99))
        elif self.weather=='ash' and len(self.weather_particles)<60:
            self.weather_particles.append(Particle(random.randint(0,WIDTH),-10,random.uniform(-30,30),random.uniform(30,80),random.uniform(2.0,4.0),(60,50,50),random.uniform(2,4),gravity=2,shape='circle',drag=0.98))
        elif self.weather=='golden' and len(self.weather_particles)<30:
            self.weather_particles.append(Particle(random.randint(0,WIDTH),random.randint(0,HEIGHT),random.uniform(-10,10),random.uniform(-20,20),random.uniform(1.5,3.0),COL_GOLD,random.uniform(2,4),gravity=0,shape='star',drag=0.99))
        if self.shake_time>0: self.shake_time-=dt; self.shake_amount*=0.92
        else: self.shake_amount=0
        for p in self.particles: p.update(ds)
        self.particles=[p for p in self.particles if p.life>0]
        for p in self.weather_particles: p.update(ds)
        self.weather_particles=[p for p in self.weather_particles if p.life>0 and p.y<HEIGHT+20]
        for ft in self.floating_texts: ft.update(ds)
        self.floating_texts=[ft for ft in self.floating_texts if ft.life>0]
        self.tweens=[t for t in self.tweens if not t.update(ds)]
        for k in self.resource_pulse: self.resource_pulse[k]=max(0,self.resource_pulse[k]-dt*2)
        for i in range(3): self.foreign_pulse[i]=max(0,self.foreign_pulse[i]-dt*2)
        self.pop_pulse=max(0,self.pop_pulse-dt*2)
        for m in self.modifiers: m.pulse_t=max(0,m.pulse_t-dt*2)
        if self.milestone_popup:
            self.milestone_popup_t+=dt
            if self.milestone_popup_t>3.0: self.milestone_popup=None
        if self.state==GameState.MENU:
            self.menu_t+=dt; self.title_anim+=dt; mp=pygame.mouse.get_pos()
            for b in self.menu_buttons:
                h=b.update(dt,mp)
                if h=="hover": self.sound.play('hover',0.5)
        elif self.state==GameState.GOV_SELECT:
            self.gov_select_t=min(1,self.gov_select_t+dt*2); mp=pygame.mouse.get_pos()
            for i,c in enumerate(self.gov_cards):
                if c["rect"].collidepoint(mp):
                    if self.gov_select_index!=i: self.gov_select_index=i; self.sound.play('hover',0.4)
                t=1.0 if i==self.gov_select_index else 0.0; c["hover_t"]+=(t-c["hover_t"])*min(1,dt*10)
        elif self.state==GameState.POLICY_SELECT:
            self.policy_select_t=min(1,self.policy_select_t+dt*2); mp=pygame.mouse.get_pos()
            for i,c in enumerate(self.policy_cards):
                if c["rect"].collidepoint(mp):
                    if self.policy_select_index!=i: self.policy_select_index=i; self.sound.play('hover',0.4)
                t=1.0 if i==self.policy_select_index else 0.0; c["hover_t"]+=(t-c["hover_t"])*min(1,dt*10)
        elif self.state==GameState.PLAYING: self.update_playing(dt,ds)
        elif self.state in (GameState.GAME_OVER,GameState.VICTORY):
            self.game_over_t=min(1,self.game_over_t+dt*1.2); mp=pygame.mouse.get_pos()
            for b in self.game_over_buttons:
                h=b.update(dt,mp)
                if h=="hover": self.sound.play('hover',0.5)
        if self.state==GameState.PLAYING and not self.research_options and not self.project_options and not self.trade_options and not self.court_candidates and not self.show_graph and not self.show_history and not self.show_stats and not self.prophecy_options:
            mp=pygame.mouse.get_pos(); self.hovered_resource=None; bw,g=140,15; tw=bw*5+g*4; sx=240+(800-tw)//2
            for i,n in enumerate(RES_ORDER):
                x=sx+i*(bw+g)
                if pygame.Rect(x,25,bw,110).collidepoint(mp): self.hovered_resource=n; break
            if pygame.Rect(WIDTH-180,20,160,110).collidepoint(mp): self.hovered_resource="rival"

    def update_playing(self, dt, ds):
        mp=pygame.mouse.get_pos()
        if self.research_options:
            self.popup_t=min(1,self.popup_t+dt*3)
            for r in self.research_buttons:
                h=r["btn"].update(dt,mp)
                if h=="hover": self.sound.play('hover',0.4)
                t=1.0 if r["btn"].hovered else 0.0; r["hover_t"]+=(t-r["hover_t"])*min(1,dt*10); return
        if self.project_options:
            self.popup_t=min(1,self.popup_t+dt*3)
            for p in self.project_buttons:
                p["btn"].disabled=self.target_resources["treasury"]<25; h=p["btn"].update(dt,mp)
                if h=="hover": self.sound.play('hover',0.4)
                t=1.0 if p["btn"].hovered else 0.0; p["hover_t"]+=(t-p["hover_t"])*min(1,dt*10); return
        if self.trade_options:
            self.popup_t=min(1,self.popup_t+dt*3)
            for t in self.trade_buttons:
                t["btn"].disabled=self.target_resources["treasury"]<20; h=t["btn"].update(dt,mp)
                if h=="hover": self.sound.play('hover',0.4)
                tg=1.0 if t["btn"].hovered else 0.0; t["hover_t"]+=(tg-t["hover_t"])*min(1,dt*10); return
        if self.court_candidates:
            self.popup_t=min(1,self.popup_t+dt*3)
            for c in self.court_buttons:
                h=c["btn"].update(dt,mp)
                if h=="hover": self.sound.play('hover',0.4)
                t=1.0 if c["btn"].hovered else 0.0; c["hover_t"]+=(t-c["hover_t"])*min(1,dt*10); return
        if self.prophecy_options:
            self.popup_t=min(1,self.popup_t+dt*3)
            for p in self.prophecy_buttons:
                h=p["btn"].update(dt,mp)
                if h=="hover": self.sound.play('hover',0.4)
                t=1.0 if p["btn"].hovered else 0.0; p["hover_t"]+=(t-p["hover_t"])*min(1,dt*10); return
        for i,b in enumerate(self.boon_buttons):
            b.disabled=self.boons_used.get(self.court[i]["name"]) or self.turn_phase!=TurnPhase.ACTIVE; b.update(dt,mp)
        for b in self.choice_buttons:
            b.disabled=(self.turn_phase!=TurnPhase.ACTIVE); h=b.update(dt,mp)
            if h=="hover": self.sound.play('hover',0.4)
        for b in self.decree_buttons:
            b.disabled=self.decree_used or self.target_resources["treasury"]<20 or self.turn_phase!=TurnPhase.ACTIVE; h=b.update(dt,mp)
            if h=="hover": self.sound.play('hover',0.4)
        if self.turn_phase==TurnPhase.INTRO:
            self.phase_timer+=dt; self.event_card_t=clamp(self.phase_timer/0.45,0,1)
            if self.phase_timer>=0.45: self.turn_phase=TurnPhase.ACTIVE; self.event_card_t=1.0
        elif self.turn_phase==TurnPhase.EFFECTS:
            self.phase_timer+=dt; self.effect_display_timer-=dt
            if self.effect_display_timer<=0:
                for k in self.target_resources: self.resources[k]=self.target_resources[k]
                self.rival_power=self.target_rival_power
                for i in range(3): self.foreign_relations[i]=self.target_foreign[i]
                self.population=self.target_population; self.check_milestones()
                if self.check_game_over():
                    self.state=GameState.GAME_OVER; self.game_over_t=0; self.sound.play('game_over'); self.shake_amount=8; self.shake_time=0.4; self.hit_stop=0.15; return
                self.turn_phase=TurnPhase.OUTRO; self.phase_timer=0
        elif self.turn_phase==TurnPhase.OUTRO:
            self.phase_timer+=dt; self.event_card_t=clamp(1-self.phase_timer/0.3,0,1)
            if self.phase_timer>=0.3: self.next_turn()
        elif self.turn_phase==TurnPhase.TRANSITION:
            self.phase_timer+=dt
            if self.phase_timer>=1.0:
                if self.pending_schedule:
                    self.pending_schedule = False
                    self.schedule_turn_event()
                else:
                    self.next_event()

    def get_shake(self):
        if self.shake_amount<=0: return (0,0)
        a=random.uniform(0,math.pi*2); return (math.cos(a)*self.shake_amount,math.sin(a)*self.shake_amount)

    def draw(self, screen, fonts):
        self._draw_bg(screen); sx,sy=self.get_shake()
        if self.state==GameState.MENU: self._draw_menu(screen,fonts,sx,sy)
        elif self.state==GameState.GOV_SELECT: self._draw_gov_select(screen,fonts,sx,sy)
        elif self.state==GameState.POLICY_SELECT: self._draw_policy_select(screen,fonts,sx,sy)
        elif self.state==GameState.PLAYING:
            self._draw_playing(screen,fonts,sx,sy)
            if self.turn_phase==TurnPhase.TRANSITION: self._draw_transition(screen,fonts)
            if self.research_options: self._draw_popup(screen,fonts,self.research_buttons,"RESEARCH BREAKTHROUGH","Choose a permanent upgrade", "ADOPT")
            if self.project_options: self._draw_popup(screen,fonts,self.project_buttons,"NATIONAL PROJECT","Invest 25 Treasury to construct", "BUILD (25T)")
            if self.trade_options: self._draw_popup(screen,fonts,self.trade_buttons,"TRADE ROUTE","Invest 20 Treasury to establish", "ESTABLISH (20T)")
            if self.court_candidates: self._draw_popup(screen,fonts,self.court_buttons,f"APPOINT NEW {['MARSHAL','CHANCELLOR','STEWARD'][self.court_role_to_fill]}","Choose a successor", "APPOINT")
            if self.prophecy_options: self._draw_popup(screen,fonts,self.prophecy_buttons,"ORACLE'S PROPHECY","Fulfill the condition in 5 years for a reward", "ACCEPT")
            if self.show_graph: self._draw_graph(screen,fonts)
            if self.show_history: self._draw_history(screen,fonts)
            if self.show_stats: self._draw_stats(screen,fonts)
        elif self.state==GameState.PAUSED: self._draw_playing(screen,fonts,sx,sy); self._draw_pause(screen,fonts)
        elif self.state==GameState.GAME_OVER: self._draw_playing(screen,fonts,sx,sy); self._draw_game_over(screen,fonts)
        elif self.state==GameState.VICTORY: self._draw_playing(screen,fonts,sx,sy); self._draw_victory(screen,fonts)
        for p in self.weather_particles: p.draw(screen)
        for p in self.particles: p.draw(screen)
        for ft in self.floating_texts: ft.draw(screen,fonts['float'])
        if self.milestone_popup: self._draw_milestone(screen,fonts)
        if self.hovered_resource and self.state==GameState.PLAYING and not self.show_graph and not self.show_history and not self.show_stats: self._draw_tooltip(screen,fonts,self.hovered_resource)
        screen.blit(self.vignette,(0,0))
        self._draw_state_overlays(screen)
        if self.flash_timer>0:
            a=int(100*(self.flash_timer/0.5)); fs=pygame.Surface((WIDTH,HEIGHT),pygame.SRCALPHA); fs.fill((*self.flash_color,a)); screen.blit(fs,(0,0))
        if self.show_debug: self._draw_debug(screen,fonts)

    def _draw_state_overlays(self, screen):
        # Civil War overlay
        at_war = any(m.name == "CIVIL WAR" for m in self.modifiers)
        if at_war:
            pulse = 0.5 + 0.5 * math.sin(pygame.time.get_ticks() * 0.005)
            col = lerp_color(COL_RED, COL_RED_BR, pulse)
            s = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            pygame.draw.rect(s, (*col, 40), (0,0,WIDTH,HEIGHT))
            screen.blit(s, (0,0))
            # Thicker, more menacing border
            pygame.draw.rect(screen, col, (6, 6, WIDTH-12, HEIGHT-12), 8, border_radius=12)
        # Golden Age overlay
        if self.state_tier == "GOLDEN AGE":
            pulse = 0.5 + 0.5 * math.sin(pygame.time.get_ticks() * 0.003)
            col = lerp_color(COL_GOLD, COL_GOLD_BR, pulse)
            # Subtle gold tint
            s = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            pygame.draw.rect(s, (*COL_GOLD, 20), (0,0,WIDTH,HEIGHT))
            screen.blit(s, (0,0))
            pygame.draw.rect(screen, col, (6, 6, WIDTH-12, HEIGHT-12), 5, border_radius=12)

    def _draw_bg(self, screen):
        tint = COL_BG
        if self.state_tier == "GOLDEN AGE": tint = (20, 25, 15)
        elif self.state_tier == "DARK AGE": tint = (25, 15, 15)
        for y in range(0,HEIGHT,4):
            t=y/HEIGHT; col=lerp_color(tint,COL_BG_GRAD,t); pygame.draw.rect(screen,col,(0,y,WIDTH,4))
        for s in self.bg_shapes:
            surf=pygame.Surface((int(s['r']*2),int(s['r']*2)),pygame.SRCALPHA)
            pygame.draw.circle(surf,(*s['color'],30),(int(s['r']),int(s['r'])),int(s['r'])); screen.blit(surf,(s['x']-s['r'],s['y']-s['r']))
        for d in self.bg_dots:
            a=int(80*d[2]); s=pygame.Surface((3,3),pygame.SRCALPHA); s.fill((180,180,200,a)); screen.blit(s,(d[0],d[1]))

    def _draw_menu(self, screen, fonts, sx, sy):
        ty=180+sy
        for i in range(5,0,-1):
            gs=fonts['title'].render("STATECRAFT",True,COL_GOLD); gs.set_alpha(int(35*(1-i/6)*(0.6+0.4*math.sin(self.title_anim*2))))
            gr=gs.get_rect(center=(WIDTH//2+sx,ty)); screen.blit(gs,gr.move(-i,0)); screen.blit(gs,gr.move(i,0)); screen.blit(gs,gr.move(0,-i)); screen.blit(gs,gr.move(0,i))
        ts=fonts['title'].render("STATECRAFT",True,COL_GOLD_BR); screen.blit(ts,ts.get_rect(center=(WIDTH//2+sx,ty)))
        sa=int(255*clamp(self.menu_t*2-0.3,0,1)); ss=fonts['sub'].render("Oracle & Ledger Edition",True,COL_TEXT); ss.set_alpha(sa)
        screen.blit(ss,ss.get_rect(center=(WIDTH//2+sx,ty+75)))
        lw=240; ls=pygame.Surface((lw,2),pygame.SRCALPHA); ls.fill((*COL_GOLD,sa)); screen.blit(ls,(WIDTH//2-lw//2+sx,ty+115+sy))
        ta=int(255*clamp(self.menu_t*2-0.6,0,1)); ts2=fonts['body'].render("Choose your path. Forge your legacy. Rule wisely.",True,COL_TEXT_DIM); ts2.set_alpha(ta)
        screen.blit(ts2,ts2.get_rect(center=(WIDTH//2+sx,ty+155+sy)))
        ba=clamp(self.menu_t*2-1.0,0,1)
        if ba>0:
            for b in self.menu_buttons: b.draw(screen,fonts['btn'])
        da=int(255*ba); dl=fonts['sm'].render("DIFFICULTY",True,COL_TEXT_DIM); dl.set_alpha(da); screen.blit(dl,(WIDTH//2-180+sx,640+sy))
        for db in self.difficulty_buttons:
            is_sel=(db["diff"]==self.difficulty); col=COL_GOLD if is_sel else COL_PANEL_LIGHT; b=COL_GOLD_BR if is_sel else COL_BORDER
            r=db["rect"].move(sx,sy); pygame.draw.rect(screen,col,r,border_radius=8); pygame.draw.rect(screen,b,r,width=2,border_radius=8)
            ts3=fonts['btn'].render(db["diff"],True,COL_TEXT_BR if is_sel else COL_TEXT); screen.blit(ts3,ts3.get_rect(center=r.center))
        ha=int(150*(0.5+0.5*math.sin(self.menu_t*3)))
        hint="SPACE to begin · ESC quit · M mute · R reduced motion · G graph · H history · J ledger · F1 debug"
        hs=fonts['sm'].render(hint,True,COL_TEXT_DIM); hs.set_alpha(ha)
        screen.blit(hs,hs.get_rect(center=(WIDTH//2,HEIGHT-50)))

    def _draw_gov_select(self, screen, fonts, sx, sy):
        t=ease_out_cubic(self.gov_select_t); ty=lerp(-100,65,t)+sy
        ts=fonts['hdr'].render("CHOOSE YOUR GOVERNMENT",True,COL_GOLD_BR); screen.blit(ts,ts.get_rect(center=(WIDTH//2+sx,int(ty))))
        ss=fonts['sm'].render("Each form of rule has unique strengths and weaknesses",True,COL_TEXT_DIM); screen.blit(ss,ss.get_rect(center=(WIDTH//2+sx,int(ty)+35)))
        for i,c in enumerate(self.gov_cards): self._draw_card(screen,fonts,c,i,t,sx,sy,"gov")
        ia=int(200*t); is_=fonts['sm'].render("← → ↑ ↓ navigate · ENTER or click to select · ESC back",True,COL_TEXT_DIM); is_.set_alpha(ia)
        screen.blit(is_,is_.get_rect(center=(WIDTH//2,HEIGHT-40+sy)))

    def _draw_policy_select(self, screen, fonts, sx, sy):
        t=ease_out_cubic(self.policy_select_t); ty=lerp(-100,65,t)+sy
        ts=fonts['hdr'].render("ENACT A POLICY",True,COL_GOLD_BR); screen.blit(ts,ts.get_rect(center=(WIDTH//2+sx,int(ty))))
        ss=fonts['sm'].render("Choose one long-term policy to guide your reign",True,COL_TEXT_DIM); screen.blit(ss,ss.get_rect(center=(WIDTH//2+sx,int(ty)+35)))
        gs=fonts['sm'].render(f"Government: {self.government.name}",True,self.government.color); screen.blit(gs,gs.get_rect(center=(WIDTH//2+sx,int(ty)+60)))
        for i,c in enumerate(self.policy_cards): self._draw_card(screen,fonts,c,i,t,sx,sy,"policy")
        ia=int(200*t); is_=fonts['sm'].render("← → navigate · ENTER or click to enact · ESC back",True,COL_TEXT_DIM); is_.set_alpha(ia)
        screen.blit(is_,is_.get_rect(center=(WIDTH//2,HEIGHT-40+sy)))

    def _draw_card(self, screen, fonts, card, idx, t, sx, sy, ctype):
        item=card["gov"] if ctype=="gov" else card["policy"]; ht=card["hover_t"]; st=idx*0.08
        ct=clamp((t-st)/max(0.01,1-st),0,1) if t>st else 0; ct=ease_out_back(ct)
        if ct<=0: return
        r=card["rect"].copy(); r.y+=int(lerp(80,0,ct)); a=int(255*ct); sc=1.0+ht*0.03
        sw,sh=int(r.w*sc),int(r.h*sc); r2=pygame.Rect(0,0,sw,sh); r2.center=r.center
        sh_=pygame.Surface((r2.w,r2.h),pygame.SRCALPHA); pygame.draw.rect(sh_,(0,0,0,int(120*ct)),sh_.get_rect(),border_radius=12); screen.blit(sh_,r2.move(0,6).topleft)
        bc=lerp_color(COL_PANEL,COL_PANEL_LIGHT,ht*0.5); bs=pygame.Surface((r2.w,r2.h),pygame.SRCALPHA); pygame.draw.rect(bs,(*bc,a),bs.get_rect(),border_radius=12); screen.blit(bs,r2.topleft)
        bo=lerp_color(COL_BORDER,item.color,0.3+ht*0.7); pygame.draw.rect(screen,bo,r2,width=2+int(ht*2),border_radius=12)
        pygame.draw.rect(screen,item.color,(r2.x,r2.y,r2.w,6),border_top_left_radius=12,border_top_right_radius=12)
        self._draw_icon(screen,item,r2.centerx,r2.y+42,26,a)
        ns=fonts['card'].render(item.name,True,COL_TEXT_BR); ns.set_alpha(a); screen.blit(ns,ns.get_rect(center=(r2.centerx,r2.y+90)))
        ts=fonts['sm'].render(f'"{item.tagline}"' if ctype=="gov" else f'{item["effects"]}',True,item.color); ts.set_alpha(a); screen.blit(ts,ts.get_rect(center=(r2.centerx,r2.y+118)))
        self._draw_wrap(screen,fonts['sm'],item.description if ctype=="gov" else item["description"],r2.x+16,r2.y+142,r2.w-32,COL_TEXT_DIM,a)
        bs2=fonts['sm'].render("✦ "+item.bonus if ctype=="gov" else "",True,COL_GOLD_BR); bs2.set_alpha(a); screen.blit(bs2,bs2.get_rect(center=(r2.centerx,r2.bottom-26)))
        if (ctype=="gov" and idx==self.gov_select_index) or (ctype=="policy" and idx==self.policy_select_index):
            p=0.5+0.5*math.sin(pygame.time.get_ticks()*0.005); ic=lerp_color(item.color,COL_TEXT_BR,p)
            is_=fonts['sm'].render("▼ SELECTED ▼",True,ic); screen.blit(is_,is_.get_rect(center=(r2.centerx,r2.bottom+18)))

    def _draw_icon(self, screen, item, cx, cy, sz, a=255):
        s=pygame.Surface((sz*2+4,sz*2+4),pygame.SRCALPHA); c=(sz+2,sz+2); col=(*item["color"],a); n=item.get("name","")
        if "ECONOMIC" in n or "MERCANTILISM" in n or "TREASURER" in n or "STEWARD" in n or "MINT" in n or "SPICE" in n or "GOLDEN" in n:
            pygame.draw.circle(s,col,c,sz); pygame.draw.line(s,(*COL_BG,a),(c[0]-8,c[1]-8),(c[0]+8,c[1]+8),3); pygame.draw.line(s,(*COL_BG,a),(c[0]-8,c[1]+8),(c[0]+8,c[1]-8),3)
        elif "MILITARY" in n or "MARSHAL" in n or "STANDING" in n or "WAR" in n or "IRON" in n or "SPARTAN" in n:
            pygame.draw.line(s,col,(c[0],c[1]-sz),(c[0],c[1]+sz),4); pygame.draw.line(s,col,(c[0]-sz+4,c[1]-sz+8),(c[0]+sz-4,c[1]-sz+8),4)
        elif "CULTURAL" in n or "PATRONAGE" in n or "CATHEDRAL" in n or "SILK" in n or "PEOPLE" in n or "ZENITH" in n:
            pygame.draw.circle(s,col,c,sz); pygame.draw.circle(s,(*COL_BG,a),(c[0]-6,c[1]-4),3); pygame.draw.circle(s,(*COL_BG,a),(c[0]+6,c[1]-4),3)
            pygame.draw.arc(s,(*COL_BG,a),(c[0]-8,c[1]-2,16,14),math.pi,2*math.pi,3)
        elif "DIPLOMATIC" in n or "CHANCELLOR" in n or "ENVOYS" in n:
            pts=[(c[0]-sz,c[1]-sz+5),(c[0]+sz,c[1]-sz+5),(c[0]+sz-5,c[1]+sz),(c[0]-sz+5,c[1]+sz)]; pygame.draw.polygon(s,col,pts)
        else: pygame.draw.circle(s,col,c,sz)
        screen.blit(s,(cx-sz-2,cy-sz-2))

    def _draw_wrap(self, screen, font, text, x, y, mw, color, a=255):
        words=text.split(); lines=[]; line=""
        for w in words:
            test=(line+" "+w).strip()
            if font.size(test)[0]<=mw: line=test
            else:
                if line: lines.append(line)
                line=w
        if line: lines.append(line)
        for i,ln in enumerate(lines):
            surf=font.render(ln,True,color); surf.set_alpha(a); screen.blit(surf,(x,y+i*20))

    def _draw_playing(self, screen, fonts, sx, sy):
        pygame.draw.rect(screen,COL_PANEL,(0,0,WIDTH,150)); pygame.draw.line(screen,COL_BORDER,(0,150),(WIDTH,150),2)
        self._draw_castle(screen,sx,sy)
        ys=fonts['hdr'].render(f"YEAR {self.turn}/{MAX_TURNS}",True,COL_GOLD_BR); screen.blit(ys,(110+sx,18+sy))
        tc=COL_TEXT
        if self.state_tier=="GOLDEN AGE": tc=COL_GOLD_BR
        elif self.state_tier=="DARK AGE": tc=COL_RED_BR
        ts=fonts['sm'].render(f"[{self.state_tier}]",True,tc); screen.blit(ts,(110+sx+ys.get_width()+10,28+sy))
        rs=fonts['body'].render(f"{self.ruler_title} {self.ruler_name}",True,COL_TEXT_BR); screen.blit(rs,(110+sx,55+sy))
        ds=fonts['sm'].render(f"House {self.dynasty_name}",True,COL_GOLD); screen.blit(ds,(110+sx,82+sy))
        ps=fonts['sm'].render(f"Policy: {self.policy['name']}",True,COL_TEXT_DIM); screen.blit(ps,(110+sx,102+sy))
        leg=sum(self.resources.values())+(self.turn-1)*10; ls=fonts['sm'].render(f"LEGACY: {leg}",True,COL_GOLD); screen.blit(ls,(110+sx,122+sy))
        pstr=f"POP: {self.display_population:.1f}M"; pc=COL_PINK if self.display_population>=10 else (COL_RED_BR if self.display_population<3 else COL_TEXT_DIM)
        ps2=fonts['sm'].render(pstr,True,pc); screen.blit(ps2,(280+sx,122+sy))
        wx=380+sx
        if self.weather=='rain':
            pygame.draw.line(screen,(100,150,200),(wx,122),(wx-3,128),2); pygame.draw.line(screen,(100,150,200),(wx+5,122),(wx+2,128),2); pygame.draw.line(screen,(100,150,200),(wx+10,122),(wx+7,128),2)
        elif self.weather=='snow':
            pygame.draw.circle(screen,(220,230,240),(wx,125),3); pygame.draw.circle(screen,(220,230,240),(wx+8,128),3); pygame.draw.circle(screen,(220,230,240),(wx+4,120),3)
        elif self.weather=='ash':
            pygame.draw.circle(screen,(60,50,50),(wx,125),3); pygame.draw.circle(screen,(60,50,50),(wx+8,128),3)
        elif self.weather=='golden':
            pts=[]
            for i in range(10):
                a=-math.pi/2+i*math.pi/5; r=5 if i%2==0 else 2; pts.append((wx+math.cos(a)*r,125+math.sin(a)*r))
            pygame.draw.polygon(screen,COL_GOLD,pts)
        self._draw_foreign(screen,fonts,sx,sy); self._draw_rival(screen,fonts,sx,sy)
        bw,bh,g=140,110,15; tw=bw*5+g*4; sx2=240+(800-tw)//2+sx
        for i,n in enumerate(RES_ORDER): self._draw_res_bar(screen,fonts,n,sx2+i*(bw+g),25+sy,bw,bh)
        if self.turn_phase in (TurnPhase.INTRO,TurnPhase.ACTIVE,TurnPhase.EFFECTS,TurnPhase.OUTRO): self._draw_decrees(screen,fonts,sx,sy)
        self._draw_advisors(screen,fonts,sx,sy); self._draw_mods(screen,fonts,sx,sy); self._draw_research_active(screen,fonts,sx,sy)
        if self.active_prophecy:
            pr = self.active_prophecy
            py = 160 + sy
            pulse = 0.5 + 0.5 * math.sin(pygame.time.get_ticks() * 0.004)
            col = lerp_color(pr["color"], COL_GOLD_BR, pulse)
            pygame.draw.rect(screen, col, (240+sx, py, 800, 32), border_radius=6)
            pygame.draw.rect(screen, COL_GOLD_BR, (240+sx, py, 800, 32), width=2, border_radius=6)
            
            # Draw star icon
            sx_star = 252 + sx
            sy_star = py + 16
            pts = []
            for i in range(10):
                ang = -math.pi/2 + i*math.pi/5
                r = 6 if i%2==0 else 3
                pts.append((sx_star + math.cos(ang)*r, sy_star + math.sin(ang)*r))
            pygame.draw.polygon(screen, COL_BG, pts)
            
            txt = f"PROPHECY: {pr['name']} - {pr['desc']} ({self.prophecy_end_turn - self.turn} years left)"
            screen.blit(fonts['sm'].render(txt, True, COL_BG), (268+sx, py+8))
            
        if self.current_event and not self.research_options and not self.project_options and not self.trade_options and not self.court_candidates and not self.show_graph and not self.show_history and not self.show_stats and not self.prophecy_options: self._draw_event(screen,fonts,sx,sy)
        if self.turn_phase in (TurnPhase.INTRO,TurnPhase.ACTIVE):
            ba=int(255*self.event_card_t) if self.turn_phase==TurnPhase.INTRO else 255
            for i,b in enumerate(self.choice_buttons):
                ch=self.current_event.choices[i]; self._draw_choice(screen,fonts,b,ch,i,sx,sy,ba)
        elif self.turn_phase in (TurnPhase.EFFECTS,TurnPhase.OUTRO): self._draw_effects(screen,fonts,sx,sy)
        ly=HEIGHT-130; lr=pygame.Rect(20,ly,WIDTH-40,110)
        lb=pygame.Surface((lr.w,lr.h),pygame.SRCALPHA); lb.fill((*COL_PANEL,200)); screen.blit(lb,lr.topleft)
        pygame.draw.rect(screen,COL_BORDER,lr,width=1,border_radius=8)
        lt=fonts['sm'].render("CHRONICLE",True,COL_GOLD); screen.blit(lt,(lr.x+12,lr.y+8))
        for i,e in enumerate(self.log[:4]):
            a=255-i*50; es=fonts['sm'].render(e,True,COL_TEXT_DIM); es.set_alpha(a); screen.blit(es,(lr.x+12,lr.y+30+i*20))
        ml=fonts['sm'].render(f"MILESTONES: {len(self.achieved_milestones)}/9",True,COL_GOLD_BR); screen.blit(ml,(lr.right-200,lr.y+8))
        h="1·2·3 choose · 4·5·6 nudge(10f) · Q·W·E·R·T·Y·U decrees · G graph · H history · J ledger · P pause"
        hs=fonts['tiny'].render(h,True,COL_TEXT_DIM); screen.blit(hs,hs.get_rect(center=(WIDTH//2,HEIGHT-8)))

    def _draw_graph(self, screen, fonts):
        o=pygame.Surface((WIDTH,HEIGHT),pygame.SRCALPHA); o.fill((0,0,0,230)); screen.blit(o,(0,0))
        ts=fonts['hdr'].render("REALM HISTORY",True,COL_GOLD_BR); screen.blit(ts,ts.get_rect(center=(WIDTH//2,100)))
        hs=fonts['sm'].render("Press G to close",True,COL_TEXT_DIM); screen.blit(hs,hs.get_rect(center=(WIDTH//2,140)))
        gw,gh=800,400; gx,gy=(WIDTH-gw)//2,200
        pygame.draw.rect(screen,COL_PANEL_DARK,(gx,gy,gw,gh),border_radius=12); pygame.draw.rect(screen,COL_BORDER,(gx,gy,gw,gh),width=2,border_radius=12)
        for i in range(5):
            y=gy+(gh//4)*i; pygame.draw.line(screen,COL_BORDER,(gx+10,y),(gx+gw-10,y),1)
            
        max_hist = max(1, len(self.history["treasury"]) - 1)
        for res in RES_ORDER:
            pts=[]
            for i, val in enumerate(self.history[res]):
                px = gx + 20 + i * ((gw - 40) / max_hist)
                py = gy + gh - 20 - (val / 100.0) * (gh - 40)
                pts.append((px, py))
            if len(pts) > 1:
                pygame.draw.lines(screen, RES_COL[res], False, pts, 3)
                
        # Draw Rival Power
        pts = []
        for i, val in enumerate(self.history["rival"]):
            px = gx + 20 + i * ((gw - 40) / max_hist)
            py = gy + gh - 20 - (val / 100.0) * (gh - 40)
            pts.append((px, py))
        if len(pts) > 1:
            pygame.draw.lines(screen, COL_ORANGE, False, pts, 3)

        lx, ly = gx + gw + 20, gy + 20
        for res in RES_ORDER:
            pygame.draw.circle(screen, RES_COL[res], (lx, ly), 6)
            screen.blit(fonts['sm'].render(RES_NAME[res], True, COL_TEXT), (lx + 15, ly - 10))
            ly += 30
        # Rival Legend
        pygame.draw.circle(screen, COL_ORANGE, (lx, ly), 6)
        screen.blit(fonts['sm'].render("RIVAL", True, COL_TEXT), (lx + 15, ly - 10))

    def _draw_history(self, screen, fonts):
        o=pygame.Surface((WIDTH,HEIGHT),pygame.SRCALPHA); o.fill((0,0,0,230)); screen.blit(o,(0,0))
        ts=fonts['hdr'].render("EVENT ARCHIVE",True,COL_GOLD_BR); screen.blit(ts,ts.get_rect(center=(WIDTH//2,100)))
        hs=fonts['sm'].render("Press H to close",True,COL_TEXT_DIM); screen.blit(hs,hs.get_rect(center=(WIDTH//2,140)))
        rx,ry,rw,rh=240,200,800,500
        pygame.draw.rect(screen,COL_PANEL_DARK,(rx,ry,rw,rh),border_radius=12); pygame.draw.rect(screen,COL_BORDER,(rx,ry,rw,rh),width=2,border_radius=12)
        y = ry + 20
        for entry in self.full_history[-22:]:
            es = fonts['sm'].render(entry, True, COL_TEXT)
            screen.blit(es, (rx + 20, y))
            y += 22

    def _draw_stats(self, screen, fonts):
        o=pygame.Surface((WIDTH,HEIGHT),pygame.SRCALPHA); o.fill((0,0,0,230)); screen.blit(o,(0,0))
        ts=fonts['hdr'].render("ROYAL LEDGER",True,COL_GOLD_BR); screen.blit(ts,ts.get_rect(center=(WIDTH//2,100)))
        hs=fonts['sm'].render("Press J to close",True,COL_TEXT_DIM); screen.blit(hs,hs.get_rect(center=(WIDTH//2,140)))
        rx,ry,rw,rh=340,180,600,460
        pygame.draw.rect(screen,COL_PANEL_DARK,(rx,ry,rw,rh),border_radius=12); pygame.draw.rect(screen,COL_BORDER,(rx,ry,rw,rh),width=2,border_radius=12)
        stats = [
            ("Ruler", f"{self.ruler_title} {self.ruler_name}"),
            ("House", f"House {self.dynasty_name}"),
            ("Years Ruled", f"{self.turn-1}"),
            ("Government", self.government.name),
            ("Decisions Made", str(self.stats["decisions"])),
            ("Crises Survived", str(self.stats["crises_survived"])),
            ("Decrees Issued", str(self.stats.get("decrees_issued", 0))),
            ("Boons Used", str(self.stats.get("boons_used", 0))),
            ("Total Gold Earned", f"{self.stats['gold_gained']} T"),
            ("Total Soldiers Lost", f"{self.stats['soldiers_lost']} M"),
            ("Peak Population", f"{self.stats['peak_pop']:.1f}M"),
            ("Prophecies Fulfilled", str(self.stats.get("prophecies_fulfilled", 0))),
            ("Prophecies Failed", str(self.stats.get("prophecies_failed", 0))),
            ("Active Prophecy", self.active_prophecy["name"] if self.active_prophecy else "None")
        ]
        for i, (l, v) in enumerate(stats):
            y = ry + 30 + i * 30
            screen.blit(fonts['body'].render(l, True, COL_TEXT_DIM), (rx + 40, y))
            screen.blit(fonts['body'].render(v, True, COL_GOLD_BR), (rx + 350, y))

    def _draw_castle(self, screen, sx, sy):
        if not self.government: return
        x,y,w,h=20+sx,20+sy,80,90; s=pygame.Surface((w,h),pygame.SRCALPHA)
        wc=lerp_color(self.government.color,COL_BG,0.6); rc=lerp_color(self.government.color,COL_TEXT_BR,0.2)
        if self.resources['treasury']>70: rc=COL_GOLD
        if self.resources['stability']<30: wc=lerp_color(wc,COL_RED,0.4); rc=lerp_color(rc,COL_RED,0.4)
        pygame.draw.rect(s,wc,(30,40,20,40)); pygame.draw.polygon(s,rc,[(30,40),(40,30),(50,40)])
        pygame.draw.rect(s,wc,(10,50,20,30)); pygame.draw.polygon(s,rc,[(10,50),(20,38),(30,50)])
        pygame.draw.rect(s,wc,(50,50,20,30)); pygame.draw.polygon(s,rc,[(50,50),(60,38),(70,50)])
        pygame.draw.rect(s,wc,(0,60,80,20))
        if self.weather in ['snow']:
            pygame.draw.polygon(s,(230,230,240),[(15,45),(20,39),(25,45)]); pygame.draw.polygon(s,(230,230,240),[(55,45),(60,39),(65,45)])
            pygame.draw.polygon(s,(230,230,240),[(35,40),(40,31),(45,40)]); pygame.draw.rect(s,(230,230,240),(0,78,80,2))
        if self.resources['happiness']<30:
            pygame.draw.circle(s,(50,50,50,150),(40,25),5); pygame.draw.circle(s,(80,80,80,150),(45,15),6)
            pygame.draw.polygon(s,COL_RED,[(20,60),(25,50),(30,60)]); pygame.draw.polygon(s,COL_ORANGE,[(22,58),(25,52),(28,58)])
        if self.resources['military']>60:
            pygame.draw.rect(s,COL_RED,(18,50,4,10)); pygame.draw.polygon(s,COL_RED,[(18,60),(22,60),(20,65)])
            pygame.draw.rect(s,COL_RED,(58,50,4,10)); pygame.draw.polygon(s,COL_RED,[(58,60),(62,60),(60,65)])
        if self.rival_power>40:
            cc=lerp_color(COL_PANEL_DARK,COL_RED,(self.rival_power-40)/60.0)
            pygame.draw.polygon(s,cc,[(0,80),(6,70),(12,80)]); pygame.draw.polygon(s,cc,[(68,80),(74,70),(80,80)])
            if self.rival_power>70:
                p=0.5+0.5*math.sin(pygame.time.get_ticks()*0.01); fc=lerp_color(COL_ORANGE,COL_RED,p)
                pygame.draw.circle(s,fc,(6,78),2); pygame.draw.circle(s,fc,(74,78),2)
        if self.rival_power>70:
            ss=pygame.Surface((w,h),pygame.SRCALPHA); ss.fill((0,0,0,80)); pygame.draw.rect(ss,(0,0,0,0),(0,0,w,h-self.rival_power//2)); s.blit(ss,(0,0))
        for i in range(len(self.achieved_milestones)):
            mx,my=12+i*14,12
            if mx<w-12:
                pts=[]
                for j in range(10):
                    a=-math.pi/2+j*math.pi/5; r=4 if j%2==0 else 2; pts.append((mx+math.cos(a)*r,my+math.sin(a)*r))
                pygame.draw.polygon(s,COL_GOLD_BR,pts)
        screen.blit(s,(x,y))

    def _draw_foreign(self, screen, fonts, sx, sy):
        for i,fp in enumerate(FOREIGN_POWERS):
            x=450+i*170+sx; y=15+sy; v=int(self.display_foreign[i]); p=self.foreign_pulse[i]; c=fp["color"]
            br=pygame.Rect(x,y,150,60)
            if p>0:
                g=pygame.Surface((br.w+16,br.h+16),pygame.SRCALPHA); pygame.draw.rect(g,(*c,int(40*p)),g.get_rect(),border_radius=10); screen.blit(g,(br.x-8,br.y-8))
            pygame.draw.rect(screen,COL_PANEL_DARK,br,border_radius=6); pygame.draw.rect(screen,c if v>=70 else (COL_RED_BR if v<20 else COL_BORDER),br,width=1,border_radius=6)
            ns=fonts['tiny'].render(fp["name"],True,c); screen.blit(ns,(x+6,y+4))
            vc=COL_GREEN_BR if v>=70 else (COL_RED_BR if v<20 else COL_TEXT); vs=fonts['sm'].render(str(v),True,vc); screen.blit(vs,(x+6,y+20))
            bx,by=x+6,y+48; bw,bh=138,6
            pygame.draw.rect(screen,COL_PANEL_LIGHT,(bx,by,bw,bh),border_radius=3); fw=int(bw*v/100)
            if fw>0:
                for px in range(fw):
                    t=px/max(1,fw); cc=lerp_color(lerp_color(COL_PANEL_DARK,c,0.5),c,t); pygame.draw.rect(screen,cc,(bx+px,by,1,bh))
                pygame.draw.rect(screen,c,(bx,by,fw,bh),border_radius=3)
            if v>=70:
                pts=[]
                for j in range(10):
                    a=-math.pi/2+j*math.pi/5; r=6 if j%2==0 else 3; pts.append((x+135+math.cos(a)*r,y+28+math.sin(a)*r))
                pygame.draw.polygon(screen,COL_GOLD_BR,pts)
            elif v<20:
                pygame.draw.circle(screen,COL_RED_BR,(x+135,y+28),6); pygame.draw.line(screen,COL_BG,(x+132,y+25),(x+138,y+31),2); pygame.draw.line(screen,COL_BG,(x+138,y+25),(x+132,y+31),2)

    def _draw_rival(self, screen, fonts, sx, sy):
        bw,bh=160,110; x,y=WIDTH-180+sx,20+sy; c=COL_ORANGE; p=0
        if self.rival_power>75: p=0.5+0.5*math.sin(pygame.time.get_ticks()*0.01); c=lerp_color(COL_ORANGE,COL_RED_BR,p)
        br=pygame.Rect(x,y,bw,bh); pygame.draw.rect(screen,COL_PANEL_DARK,br,border_radius=8); pygame.draw.rect(screen,c,br,width=1,border_radius=8)
        screen.blit(fonts['tiny'].render("RIVAL THREAT",True,COL_TEXT_DIM),(x+10,y+8)); screen.blit(fonts['tiny'].render(self.rival_name[:18],True,c),(x+10,y+24))
        vs=fonts['res'].render(str(int(self.display_rival_power)),True,c); screen.blit(vs,(x+10,y+40))
        bx,by=x+10,y+bh-18; bw2,bh2=bw-20,8
        pygame.draw.rect(screen,COL_PANEL_LIGHT,(bx,by,bw2,bh2),border_radius=4); fw=int(bw2*self.display_rival_power/100)
        if fw>0:
            for px in range(fw):
                t=px/max(1,fw); cc=lerp_color(lerp_color(COL_PANEL_DARK,c,0.5),c,t); pygame.draw.rect(screen,cc,(bx+px,by,1,bh2))
            pygame.draw.rect(screen,c,(bx,by,fw,bh2),border_radius=4)
            
        d=int(self.target_rival_power-self.display_rival_power)
        if abs(d)>0:
            # Green if rival power is dropping (d < 0), Red if rising (d > 0)
            cc=COL_GREEN_BR if d < 0 else COL_RED_BR
            s="-" if d < 0 else "+"
            screen.blit(fonts['tiny'].render(f"{s}{abs(d)}",True,cc),(x+bw-38,y+44))

    def _draw_decrees(self, screen, fonts, sx, sy):
        for i,b in enumerate(self.decree_buttons):
            d=DECREES[i]; r=b.rect.move(sx,sy+int(b.press_anim*2))
            sh=pygame.Surface((r.w,r.h),pygame.SRCALPHA); pygame.draw.rect(sh,(0,0,0,80),sh.get_rect(),border_radius=8); screen.blit(sh,r.move(0,3).topleft)
            bg=lerp_color(COL_PANEL_LIGHT,COL_BORDER_BR,b.hover_t*0.35) if not b.disabled else COL_PANEL_DARK
            pygame.draw.rect(screen,bg,r,border_radius=8)
            bc=lerp_color(COL_BORDER,d["color"],0.5+b.hover_t*0.5) if not b.disabled else COL_BORDER
            pygame.draw.rect(screen,bc,r,width=2,border_radius=8)
            key_txt = chr(DECREE_KEYS[i]) if i < len(DECREE_KEYS) else ""
            screen.blit(fonts['tiny'].render(f"[{key_txt}] {d['name']}",True,COL_TEXT_BR if not b.disabled else COL_TEXT_DIM),(r.x+8,r.y+4))
            screen.blit(fonts['tiny'].render(f"-{d['cost']} T",True,COL_GOLD if not b.disabled else COL_TEXT_DIM),(r.x+8,r.y+20))
            hm="modifiers" in d
            for rs,vl in d["effects"].items():
                if vl>0 and rs!="rival":
                    self._draw_mini(screen,rs,r.x+r.w-30,r.y+20,d["color"] if not b.disabled else COL_TEXT_DIM)
                    screen.blit(fonts['tiny'].render(f"+{vl}",True,d["color"] if not b.disabled else COL_TEXT_DIM),(r.x+r.w-18,r.y+20)); break
                elif rs=="rival" and vl<0:
                    pygame.draw.circle(screen,d["color"] if not b.disabled else COL_TEXT_DIM,(r.x+r.w-20,r.y+24),6)
                    screen.blit(fonts['tiny'].render(f"{vl}",True,d["color"] if not b.disabled else COL_TEXT_DIM),(r.x+r.w-12,r.y+20)); break
                elif hm:
                    screen.blit(fonts['tiny'].render("+MOD",True,d["color"] if not b.disabled else COL_TEXT_DIM),(r.x+r.w-35,r.y+20)); break
            if "foreign" in d:
                fs=fonts['tiny'].render("+FP" if d["foreign"].get("rand") is None else "ESP",True,COL_CYAN if not b.disabled else COL_TEXT_DIM)
                screen.blit(fs,(r.x+r.w-35,r.y+20))

    def _draw_advisors(self, screen, fonts, sx, sy):
        for i,a in enumerate(self.court):
            y=170+i*160; r=pygame.Rect(20+sx,y+sy,200,150)
            pygame.draw.rect(screen,COL_PANEL,r,border_radius=10); pygame.draw.rect(screen,a["color"],r,width=2,border_radius=10)
            self._draw_icon(screen,a,r.x+30,r.y+35,14,255)
            screen.blit(fonts['sm'].render(a["name"],True,COL_TEXT_BR),(r.x+55,r.y+20))
            screen.blit(fonts['tiny'].render(a["role"],True,COL_TEXT_DIM),(r.x+55,r.y+40))
            dt=" / ".join([f"{'+' if v>0 else ''}{v} {k[:3].upper()}" for k,v in a["drift"].items()])
            screen.blit(fonts['tiny'].render(dt,True,a["color"]),(r.x+10,r.y+58))
            bt=f"Boon: {a.get('boon','')}"
            screen.blit(fonts['tiny'].render(bt,True,COL_GOLD_BR if not self.boons_used.get(a["name"]) else COL_TEXT_DIM),(r.x+10,r.y+72))
            sa=(self.turn_phase in (TurnPhase.ACTIVE,TurnPhase.INTRO) and a["name"] in self.advisor_advice)
            sr=(a["name"] in self.advisor_reactions and self.turn_phase in (TurnPhase.EFFECTS,TurnPhase.OUTRO))
            if sa or sr:
                if sr: m=self.advisor_reactions[a["name"]]; idx=self.selected_choice_idx; bc=COL_GOLD_BR; lb="REACTION"
                else: idx,m=self.advisor_advice[a["name"]]; bc=a["color"]; lb="ADVICE"
                br=pygame.Rect(r.x+10,r.y+90,r.w-20,35); pygame.draw.rect(screen,COL_PANEL_LIGHT,br,border_radius=8); pygame.draw.rect(screen,bc,br,width=1,border_radius=8)
                screen.blit(fonts['tiny'].render(lb,True,bc),(br.x+8,br.y+4))
                self._draw_wrap(screen,fonts['tiny'],m,br.x+8,br.y+16,br.w-16,COL_TEXT)
            self.boon_buttons[i].draw(screen,fonts['tiny'])

    def _draw_mods(self, screen, fonts, sx, sy):
        rx,ry=1060+sx,170+sy; screen.blit(fonts['sm'].render("ACTIVE EFFECTS",True,COL_GOLD_BR),(rx,ry))
        for i,m in enumerate(self.modifiers):
            y=ry+30+i*85; mr=pygame.Rect(rx,y,200,75); p=m.pulse_t
            if p>0:
                g=pygame.Surface((mr.w+16,mr.h+16),pygame.SRCALPHA); pygame.draw.rect(g,(*m.color,int(60*p)),g.get_rect(),border_radius=12); screen.blit(g,(mr.x-8,mr.y-8))
            pygame.draw.rect(screen,COL_PANEL,mr,border_radius=8); pygame.draw.rect(screen,m.color,mr,width=2,border_radius=8)
            screen.blit(fonts['sm'].render(m.name,True,m.color),(mr.x+10,mr.y+8))
            dt=" / ".join([f"{'+' if v>0 else ''}{v} {k[:3].upper()}" for k,v in m.drift.items()])
            screen.blit(fonts['tiny'].render(dt,True,COL_TEXT_DIM),(mr.x+10,mr.y+32))
            for p in range(m.max_duration):
                c=m.color if p<m.duration else COL_PANEL_DARK; pygame.draw.circle(screen,c,(mr.x+10+p*15,mr.y+55),5)

    def _draw_research_active(self, screen, fonts, sx, sy):
        if not self.permanent_drifts: return
        rx,ry=1060+sx,400+sy; screen.blit(fonts['sm'].render("BONUSES",True,COL_TEAL),(rx,ry))
        for i,r in enumerate(self.permanent_drifts):
            y=ry+25+i*25; screen.blit(fonts['tiny'].render(r["name"],True,r["color"]),(rx,y))
            dt=" / ".join([f"{'+' if v>0 else ''}{v} {k[:3].upper()}" for k,v in r["drift"].items()])
            screen.blit(fonts['tiny'].render(dt,True,COL_TEXT_DIM),(rx+110,y))

    def _draw_res_bar(self, screen, fonts, n, x, y, w, h):
        v=int(self.display_resources[n]); t=self.target_resources[n]; c=RES_COL[n]; p=self.resource_pulse[n]; br=pygame.Rect(x,y,w,h)
        if p>0:
            g=pygame.Surface((w+20,h+20),pygame.SRCALPHA); pygame.draw.rect(g,(*c,int(60*p)),g.get_rect(),border_radius=12); screen.blit(g,(x-10,y-10))
        if v<=15:
            cp=0.5+0.5*math.sin(pygame.time.get_ticks()*0.01); g=pygame.Surface((w+20,h+20),pygame.SRCALPHA); pygame.draw.rect(g,(*COL_RED,int(80*cp)),g.get_rect(),border_radius=12); screen.blit(g,(x-10,y-10))
        pygame.draw.rect(screen,COL_PANEL_DARK,br,border_radius=8); pygame.draw.rect(screen,COL_BORDER,br,width=1,border_radius=8)
        self._draw_mini(screen,n,x+22,y+22,11,c); screen.blit(fonts['tiny'].render(RES_NAME[n],True,COL_TEXT_DIM),(x+40,y+14))
        vc=lerp_color(COL_TEXT_BR,c,p*0.5); screen.blit(fonts['res'].render(str(v),True,vc),(x+12,y+36))
        bx,by=x+12,y+h-18; bw,bh=w-24,8
        pygame.draw.rect(screen,COL_PANEL_LIGHT,(bx,by,bw,bh),border_radius=4); fw=int(bw*v/100)
        if fw>0:
            for px in range(fw):
                t=px/max(1,fw); cc=lerp_color(lerp_color(COL_PANEL_DARK,c,0.5),c,t); pygame.draw.rect(screen,cc,(bx+px,by,1,bh))
            pygame.draw.rect(screen,c,(bx,by,fw,bh),border_radius=4)
        d=int(t-v)
        if abs(d)>0:
            cc=COL_GREEN_BR if d>0 else COL_RED_BR; s="+" if d>0 else ""; screen.blit(fonts['tiny'].render(f"{s}{d}",True,cc),(x+w-38,y+44))

    def _draw_mini(self, screen, n, x, y, c):
        s=pygame.Surface((14,14),pygame.SRCALPHA)
        if n=="treasury":
            pygame.draw.circle(s,c,(7,7),6); pygame.draw.circle(s,lerp_color(c,COL_TEXT_BR,0.4),(7,7),6,1)
        elif n=="influence":
            pts=[]
            for i in range(10):
                a=-math.pi/2+i*math.pi/5; r=6 if i%2==0 else 2.5; pts.append((7+math.cos(a)*r,7+math.sin(a)*r))
            pygame.draw.polygon(s,c,pts)
        elif n=="happiness":
            pygame.draw.circle(s,c,(7,7),6); pygame.draw.circle(s,COL_BG,(5,6),1); pygame.draw.circle(s,COL_BG,(9,6),1)
        elif n=="stability":
            pts=[(2,2),(12,2),(12,8),(7,12),(2,8)]; pygame.draw.polygon(s,c,pts)
        elif n=="military":
            pygame.draw.line(s,c,(7,1),(7,11),2); pygame.draw.line(s,c,(3,4),(11,4),2)
        screen.blit(s,(x,y))

    def _draw_event(self, screen, fonts, sx, sy):
        t=ease_out_cubic(self.event_card_t); cw,ch=760,140; cx=240+(800-cw)//2+sx-int(lerp(80,0,t)); cy=190+sy; a=int(255*t)
        cat=self.current_event.category; cc=COL_GOLD if cat=="ECONOMIC" else (COL_RED if cat=="MILITARY" else (COL_GREEN if cat=="SOCIAL" else (COL_PURPLE if cat=="DIPLOMATIC" else (COL_RED_BR if cat=="CRISIS" else COL_TEAL))))
        sh=pygame.Surface((cw,ch),pygame.SRCALPHA); pygame.draw.rect(sh,(0,0,0,120),sh.get_rect(),border_radius=14); screen.blit(sh,(cx,cy+8))
        cs=pygame.Surface((cw,ch),pygame.SRCALPHA); pygame.draw.rect(cs,(*COL_PANEL,a),cs.get_rect(),border_radius=14); screen.blit(cs,(cx,cy))
        pygame.draw.rect(screen,lerp_color(COL_BORDER,cc,t),(cx,cy,cw,ch),width=2,border_radius=14)
        pygame.draw.rect(screen,cc,(cx,cy,cw,4),border_top_left_radius=14,border_top_right_radius=14)
        self._draw_icon(screen,{"name":cat,"color":cc},cx+cw-70,cy+60,25,a)
        bs=fonts['tiny'].render(cat,True,cc); screen.blit(bs,bs.get_rect(topright=(cx+cw-20,cy+12)))
        if self.current_event.is_crisis:
            cp=0.5+0.5*math.sin(pygame.time.get_ticks()*0.008); cl=lerp_color(COL_RED,COL_RED_BR,cp)
            screen.blit(fonts['tiny'].render("⚠ CRISIS",True,cl),(cx+cw-120,cy+28))
        ts=fonts['hdr'].render(self.current_event.title,True,COL_GOLD_BR); ts.set_alpha(a); screen.blit(ts,(cx+24,cy+16))
        self._draw_wrap(screen,fonts['body'],self.current_event.description,cx+24,cy+58,cw-120,COL_TEXT,a)

    def _draw_choice(self, screen, fonts, b, ch, idx, sx, sy, a=255):
        r=b.rect.move(sx,sy+int(b.press_anim*2))
        sh=pygame.Surface((r.w,r.h),pygame.SRCALPHA); pygame.draw.rect(sh,(0,0,0,100),sh.get_rect(),border_radius=10); screen.blit(sh,r.move(0,4).topleft)
        bg=lerp_color(COL_PANEL_LIGHT,COL_BORDER_BR,b.hover_t*0.35); bs=pygame.Surface((r.w,r.h),pygame.SRCALPHA); pygame.draw.rect(bs,(*bg,a),bs.get_rect(),border_radius=10); screen.blit(bs,r.topleft)
        bc=lerp_color(COL_BORDER,COL_GOLD_BR,b.hover_t); bs2=pygame.Surface((r.w,r.h),pygame.SRCALPHA); pygame.draw.rect(bs2,(*bc,a),bs2.get_rect(),width=2,border_radius=10); screen.blit(bs2,r.topleft)
        nx,ny=r.x+35,r.centery; nc=lerp_color(COL_GOLD,COL_GOLD_BR,b.hover_t)
        pygame.draw.circle(screen,nc,(nx,ny),20); pygame.draw.circle(screen,COL_BG,(nx,ny),20,2)
        ns=fonts['btn'].render(str(idx+1),True,COL_BG); screen.blit(ns,ns.get_rect(center=(nx,ny)))
        tx=r.x+75; screen.blit(fonts['body'].render(ch.text,True,COL_TEXT_BR),(tx,r.y+12))
        ex,ey=tx,r.y+38
        for rs,dl in ch.effects.items():
            if rs=="rival":
                c=COL_ORANGE if dl<0 else COL_RED_BR; s="+" if dl>0 else ""; pygame.draw.circle(screen,c,(ex+7,ey+8),6)
                es=fonts['sm'].render(f"{s}{dl} RIV",True,c); screen.blit(es,(ex+18,ey)); ex+=18+es.get_width()+16; continue
            c=COL_GREEN_BR if dl>0 else COL_RED_BR; s="+" if dl>0 else ""; self._draw_mini(screen,rs,ex,ey+2,c)
            es=fonts['sm'].render(f"{s}{dl}",True,c); screen.blit(es,(ex+18,ey)); ex+=18+es.get_width()+16
        if ch.foreign:
            for fn,dl in ch.foreign.items():
                fp=next(f for f in FOREIGN_POWERS if f["name"].lower()==fn); c=COL_GREEN_BR if dl>0 else COL_RED_BR; s="+" if dl>0 else ""
                fs=fonts['sm'].render(f"{s}{dl} {fp['name'][:3]}",True,c); screen.blit(fs,(ex,ey)); ex+=fs.get_width()+16
        if ch.check:
            ct=fonts['tiny'].render(f"CHECK: {ch.check['stat'].upper()}",True,COL_CYAN); screen.blit(ct,(ex,ey+4)); ex+=ct.get_width()+12
        if ch.modifiers: screen.blit(fonts['tiny'].render(" + EFFECTS",True,COL_PURPLE),(ex,ey+4))
        if ch.queue: screen.blit(fonts['tiny'].render(" → CHAIN",True,COL_TEAL),(ex,ey+4))
        can_nudge = self.target_resources["influence"]>=10 and self.difficulty != "IRONMAN"
        if can_nudge and not b.disabled:
            nk=idx+4; ns=fonts['tiny'].render(f"[{nk}] Nudge 10f",True,COL_PURPLE); screen.blit(ns,(r.right-ns.get_width()-15,r.y+12))
        elif self.difficulty == "IRONMAN" and not b.disabled:
            ns=fonts['tiny'].render("IRONMAN: NO NUDGE",True,COL_TEXT_DIM); screen.blit(ns,(r.right-ns.get_width()-15,r.y+12))

    def _draw_effects(self, screen, fonts, sx, sy):
        if self.selected_choice_idx is None: return
        ch=self.current_event.choices[self.selected_choice_idx]
        t=clamp(self.phase_timer/0.4,0,1) if self.turn_phase==TurnPhase.EFFECTS else 1.0; a=int(255*t)
        y=340+sy; x=240+(800-760)//2+sx; w,h=760,215; r=pygame.Rect(x,y,w,h)
        bs=pygame.Surface((w,h),pygame.SRCALPHA); pygame.draw.rect(bs,(*COL_PANEL,a),bs.get_rect(),border_radius=10); screen.blit(bs,r.topleft)
        pygame.draw.rect(screen,lerp_color(COL_BORDER,COL_GOLD,t),r,width=2,border_radius=10)
        lt="YOUR DECISION"
        if self.nudged: lt+=" (NUDGED)"
        if self.check_result: lt+=f" - {self.check_result}!"
        lc=COL_GOLD_BR if self.nudged else COL_PURPLE
        if self.check_result=="SUCCESS": lc=COL_GREEN_BR
        elif self.check_result=="FAILURE": lc=COL_RED_BR
        ls=fonts['sm'].render(lt,True,lc); ls.set_alpha(a); screen.blit(ls,(r.x+24,r.y+16))
        ts=fonts['hdr'].render(ch.text,True,COL_TEXT_BR); ts.set_alpha(a); screen.blit(ts,(r.x+24,r.y+42))
        ex,ey=r.x+24,r.y+90; ets=ch.effects.copy()
        if self.check_result=="SUCCESS":
            for k,v in ch.check["success"].items(): ets[k]=ets.get(k,0)+v
        elif self.check_result=="FAILURE":
            for k,v in ch.check["failure"].items(): ets[k]=ets.get(k,0)+v
        if self.nudged:
            for rs,vl in ets.items():
                if vl>0: ets[rs]=vl+5
                elif vl<0: ets[rs]=vl+5
        for rs,dl in ets.items():
            if rs=="rival":
                c=COL_ORANGE if dl<0 else COL_RED_BR; s="+" if dl>0 else ""; pygame.draw.circle(screen,c,(ex+8,ey+12),8)
                es=fonts['body'].render(f"{s}{dl} RIVAL POWER",True,c); es.set_alpha(a); screen.blit(es,(ex+20,ey)); ex+=20+es.get_width()+24; continue
            c=COL_GREEN_BR if dl>0 else COL_RED_BR; s="+" if dl>0 else ""; self._draw_mini(screen,rs,ex,ey+2,c)
            es=fonts['body'].render(f"{s}{dl} {RES_NAME[rs]}",True,c); es.set_alpha(a); screen.blit(es,(ex+18,ey)); ex+=18+es.get_width()+24
        if ch.foreign:
            fx,fy=r.x+24,r.y+120; fl=fonts['sm'].render("FOREIGN RELATIONS:",True,COL_CYAN); fl.set_alpha(a); screen.blit(fl,(fx,fy)); fx+=fl.get_width()+12
            for fn,dl in ch.foreign.items():
                fp=next(f for f in FOREIGN_POWERS if f["name"].lower()==fn); c=COL_GREEN_BR if dl>0 else COL_RED_BR; s="+" if dl>0 else ""
                es=fonts['body'].render(f"{s}{dl} {fp['name']}",True,c); es.set_alpha(a); screen.blit(es,(fx,fy)); fx+=es.get_width()+16
        if ch.modifiers:
            my=r.y+150 if ch.foreign else r.y+140; ml=fonts['sm'].render("NEW ACTIVE EFFECTS:",True,COL_PURPLE); ml.set_alpha(a); screen.blit(ml,(r.x+24,my))
            mx,mty=r.x+24,my+24
            for md in ch.modifiers:
                ms=fonts['body'].render(f"• {md['name']} ({md['duration']} turns)",True,md["color"]); ms.set_alpha(a); screen.blit(ms,(mx,mty)); mx+=ms.get_width()+24
        if ch.queue:
            cy=r.y+180 if ch.modifiers else (r.y+160 if ch.foreign else r.y+140)
            cl=fonts['sm'].render("CONSEQUENCES WILL FOLLOW...",True,COL_TEAL); cl.set_alpha(a); screen.blit(cl,(r.x+24,cy))

    def _draw_transition(self, screen, fonts):
        t=self.phase_timer/1.0; a=int(255*math.sin(t*math.pi)); txt=f"YEAR {self.turn}"
        ts=fonts['title'].render(txt,True,COL_GOLD_BR); ts.set_alpha(a)
        ox = lerp(-200, 200, ease_in_out_cubic(t)) if self.pending_schedule else 0
        screen.blit(ts,ts.get_rect(center=(WIDTH//2+int(ox),HEIGHT//2)))

    def _draw_popup(self, screen, fonts, btns, title, sub, btn_txt):
        t=ease_out_cubic(self.popup_t); o=pygame.Surface((WIDTH,HEIGHT),pygame.SRCALPHA); o.fill((0,0,0,int(180*t))); screen.blit(o,(0,0))
        ts=fonts['hdr'].render(title,True,COL_GOLD_BR); ts.set_alpha(int(255*t)); screen.blit(ts,ts.get_rect(center=(WIDTH//2,HEIGHT//2-180)))
        ss=fonts['sm'].render(sub,True,COL_TEXT_DIM); ss.set_alpha(int(255*t)); screen.blit(ss,ss.get_rect(center=(WIDTH//2,HEIGHT//2-145)))
        for i,b in enumerate(btns):
            item=b["res"] if "res" in b else (b["proj"] if "proj" in b else (b["trade"] if "trade" in b else (b["prop"] if "prop" in b else b["cand"])))
            ht=b["hover_t"]; st=i*0.1
            ct=clamp((t-st)/max(0.01,1-st),0,1) if t>st else 0; ct=ease_out_back(ct)
            if ct<=0: continue
            r=b["btn"].rect; sc=1.0+ht*0.05; sw,sh=int(r.w*sc),int(r.h*sc); r2=pygame.Rect(0,0,sw,sh); r2.center=r.center
            sh_=pygame.Surface((r2.w,r2.h),pygame.SRCALPHA); pygame.draw.rect(sh_,(0,0,0,int(150*ct)),sh_.get_rect(),border_radius=12); screen.blit(sh_,r2.move(0,6).topleft)
            bc=lerp_color(COL_PANEL,COL_PANEL_LIGHT,ht*0.5); bs=pygame.Surface((r2.w,r2.h),pygame.SRCALPHA); pygame.draw.rect(bs,(*bc,int(255*ct)),bs.get_rect(),border_radius=12); screen.blit(bs,r2.topleft)
            bo=lerp_color(COL_BORDER,item["color"],0.3+ht*0.7); pygame.draw.rect(screen,bo,r2,width=2+int(ht*2),border_radius=12)
            pygame.draw.rect(screen,item["color"],(r2.x,r2.y,r2.w,6),border_top_left_radius=12,border_top_right_radius=12)
            self._draw_icon(screen,item,r2.centerx,r2.y+60,28,int(255*ct))
            ns=fonts['card'].render(item["name"],True,COL_TEXT_BR); ns.set_alpha(int(255*ct)); screen.blit(ns,ns.get_rect(center=(r2.centerx,r2.y+115)))
            ds=fonts['sm'].render(item.get("desc",item.get("role","")),True,COL_TEXT_DIM); ds.set_alpha(int(255*ct)); screen.blit(ds,ds.get_rect(center=(r2.centerx,r2.y+145)))
            if "drift" in item:
                dt=" / ".join([f"{'+' if v>0 else ''}{v} {k[:3].upper()}" for k,v in item["drift"].items()])
                ds2=fonts['sm'].render(dt,True,item["color"]); ds2.set_alpha(int(255*ct)); screen.blit(ds2,ds2.get_rect(center=(r2.centerx,r2.bottom-60)))
            elif "reward" in item:
                rw_txt="Reward: " + " / ".join([f"{'+' if v>0 else ''}{v} {k[:3].upper()}" for k,v in item["reward"].items()])
                pn_txt="Penalty: " + " / ".join([f"{'+' if v>0 else ''}{v} {k[:3].upper()}" for k,v in item["penalty"].items()])
                ds2=fonts['sm'].render(rw_txt,True,COL_GREEN_BR); ds2.set_alpha(int(255*ct)); screen.blit(ds2,ds2.get_rect(center=(r2.centerx,r2.bottom-90)))
                ds3=fonts['sm'].render(pn_txt,True,COL_RED_BR); ds3.set_alpha(int(255*ct)); screen.blit(ds3,ds3.get_rect(center=(r2.centerx,r2.bottom-60)))
            b["btn"].draw(screen,fonts['btn'])

    def _draw_pause(self, screen, fonts):
        o=pygame.Surface((WIDTH,HEIGHT),pygame.SRCALPHA); o.fill((0,0,0,180)); screen.blit(o,(0,0))
        ps=fonts['title'].render("PAUSED",True,COL_GOLD_BR); screen.blit(ps,ps.get_rect(center=(WIDTH//2,HEIGHT//2-30)))
        hs=fonts['body'].render("Press P or ESC to resume",True,COL_TEXT_DIM); screen.blit(hs,hs.get_rect(center=(WIDTH//2,HEIGHT//2+30)))

    def _draw_game_over(self, screen, fonts):
        t=ease_out_cubic(self.game_over_t); o=pygame.Surface((WIDTH,HEIGHT),pygame.SRCALPHA); o.fill((0,0,0,int(200*t))); screen.blit(o,(0,0))
        ty=lerp(-100,130,t); ts=fonts['title'].render("REIGN ENDED",True,COL_RED_BR); screen.blit(ts,ts.get_rect(center=(WIDTH//2,int(ty))))
        if t>0.3:
            ct=clamp((t-0.3)/0.4,0,1); a=int(255*ct); cs=fonts['body'].render(self.cause_of_death,True,COL_TEXT); cs.set_alpha(a)
            screen.blit(cs,cs.get_rect(center=(WIDTH//2,210)))
        if t>0.4:
            ct=clamp((t-0.4)/0.4,0,1); a=int(255*ct); px,py=WIDTH//2-250,260; pw,ph=500,420
            ps=pygame.Surface((pw,ph),pygame.SRCALPHA); pygame.draw.rect(ps,(*COL_PANEL,int(220*ct)),ps.get_rect(),border_radius=12); screen.blit(ps,(px,py))
            pygame.draw.rect(screen,lerp_color(COL_BORDER,COL_GOLD,ct),(px,py,pw,ph),width=2,border_radius=12)
            leg=sum(self.resources.values())+(self.turn-1)*10; rk,rc=self.compute_rank(leg)
            stats=[("Ruler",f"{self.ruler_title} {self.ruler_name}"),("House",f"House {self.dynasty_name}"),("Years Ruled",f"{self.turn-1}"),
                   ("Government",self.government.name),("Policy",self.policy['name']),("Decisions Made",str(self.stats["decisions"])),
                   ("Crises Survived",str(self.stats["crises_survived"])),("Decrees Issued",str(self.stats.get("decrees_issued",0))),
                   ("Boons Used",str(self.stats.get("boons_used",0))),("Gold Earned",str(self.stats["gold_gained"])),
                   ("Soldiers Lost",str(self.stats["soldiers_lost"])),("Peak Population",f"{self.stats['peak_pop']:.1f}M"),
                   ("Prophecies Fulfilled",str(self.stats.get("prophecies_fulfilled",0))),
                   ("Prophecies Failed",str(self.stats.get("prophecies_failed",0))),
                   ("Milestones",f"{len(self.achieved_milestones)}/9"),("Legacy Score",str(leg)),("Rank",rk)]
            for i,(l,v) in enumerate(stats):
                ly=py+16+i*22; ls=fonts['body'].render(l,True,COL_TEXT_DIM); ls.set_alpha(a); screen.blit(ls,(px+24,ly))
                vs=fonts['body'].render(v,True,rc if l=="Rank" else COL_GOLD_BR); vs.set_alpha(a); screen.blit(vs,(px+pw-24-vs.get_width(),ly))
        if t>0.7:
            for b in self.game_over_buttons: b.draw(screen,fonts['btn'])

    def _draw_victory(self, screen, fonts):
        t=ease_out_cubic(self.game_over_t); o=pygame.Surface((WIDTH,HEIGHT),pygame.SRCALPHA); o.fill((20,30,50,int(180*t))); screen.blit(o,(0,0))
        ty=lerp(-100,130,t); gp=0.7+0.3*math.sin(pygame.time.get_ticks()*0.003)
        for i in range(5,0,-1):
            gs=fonts['title'].render("VICTORY!",True,COL_GOLD); gs.set_alpha(int(40*gp*(1-i/6)))
            gr=gs.get_rect(center=(WIDTH//2,int(ty))); screen.blit(gs,gr.move(-i,0)); screen.blit(gs,gr.move(i,0)); screen.blit(gs,gr.move(0,-i)); screen.blit(gs,gr.move(0,i))
        ts=fonts['title'].render("VICTORY!",True,COL_GOLD_BR); screen.blit(ts,ts.get_rect(center=(WIDTH//2,int(ty))))
        if t>0.3:
            ct=clamp((t-0.3)/0.4,0,1); a=int(255*ct); ms=fonts['hdr'].render("Your reign stands the test of time.",True,COL_TEXT_BR); ms.set_alpha(a)
            screen.blit(ms,ms.get_rect(center=(WIDTH//2,210)))
        if t>0.4:
            ct=clamp((t-0.4)/0.4,0,1); a=int(255*ct); px,py=WIDTH//2-250,260; pw,ph=500,380
            ps=pygame.Surface((pw,ph),pygame.SRCALPHA); pygame.draw.rect(ps,(*COL_PANEL,int(220*ct)),ps.get_rect(),border_radius=12); screen.blit(ps,(px,py))
            pygame.draw.rect(screen,lerp_color(COL_BORDER,COL_GOLD,ct),(px,py,pw,ph),width=2,border_radius=12)
            leg=sum(self.resources.values())+(self.turn-1)*10; rk,rc=self.compute_rank(leg)
            ry=py-40; rs=fonts['title'].render(f"RANK: {rk}",True,rc); rs.set_alpha(a); screen.blit(rs,rs.get_rect(center=(WIDTH//2,ry)))
            stats=[("Ruler",f"{self.ruler_title} {self.ruler_name}"),("House",f"House {self.dynasty_name}"),("Years Ruled",f"{self.turn-1}"),
                   ("Government",self.government.name),("Policy",self.policy['name']),("Decisions Made",str(self.stats["decisions"])),
                   ("Crises Survived",str(self.stats["crises_survived"])),("Decrees Issued",str(self.stats.get("decrees_issued",0))),
                   ("Boons Used",str(self.stats.get("boons_used",0))),("Gold Earned",str(self.stats["gold_gained"])),
                   ("Soldiers Lost",str(self.stats["soldiers_lost"])),("Peak Population",f"{self.stats['peak_pop']:.1f}M"),
                   ("Prophecies Fulfilled",str(self.stats.get("prophecies_fulfilled",0))),
                   ("Prophecies Failed",str(self.stats.get("prophecies_failed",0))),
                   ("Milestones",f"{len(self.achieved_milestones)}/9"),("Legacy Score",str(leg))]
            for i,(l,v) in enumerate(stats):
                ly=py+16+i*22; ls=fonts['body'].render(l,True,COL_TEXT_DIM); ls.set_alpha(a); screen.blit(ls,(px+24,ly))
                vs=fonts['body'].render(v,True,COL_GOLD_BR); vs.set_alpha(a); screen.blit(vs,(px+pw-24-vs.get_width(),ly))
        if t>0.7:
            for b in self.game_over_buttons: b.draw(screen,fonts['btn'])

    def _draw_milestone(self, screen, fonts):
        m=self.milestone_popup; t=self.milestone_popup_t
        if t<0.3: at=ease_out_back(t/0.3)
        elif t<2.5: at=1.0
        else: at=ease_in_cubic(1-(t-2.5)/0.5)
        if at<=0: return
        w,h=500,90; x=(WIDTH-w)//2; y=int(lerp(-100,160,at)); a=int(255*clamp(at,0,1))
        bg=pygame.Surface((w,h),pygame.SRCALPHA); pygame.draw.rect(bg,(*COL_PANEL,a),bg.get_rect(),border_radius=12); screen.blit(bg,(x,y))
        pygame.draw.rect(screen,lerp_color(COL_BORDER,m["color"],at),(x,y,w,h),width=2,border_radius=12)
        pygame.draw.rect(screen,m["color"],(x,y,w,4),border_top_left_radius=12,border_top_right_radius=12)
        sx,sy=x+45,y+h//2; s=pygame.Surface((50,50),pygame.SRCALPHA); pts=[]
        for i in range(10):
            a2=-math.pi/2+i*math.pi/5; r=22 if i%2==0 else 10; pts.append((25+math.cos(a2)*r,25+math.sin(a2)*r))
        pygame.draw.polygon(s,(*m["color"],a),pts); screen.blit(s,(sx-25,sy-25))
        ls=fonts['tiny'].render("MILESTONE ACHIEVED",True,COL_GOLD_BR); ls.set_alpha(a); screen.blit(ls,(x+80,y+14))
        ts=fonts['hdr'].render(m["title"],True,m["color"]); ts.set_alpha(a); screen.blit(ts,(x+80,y+32))
        ds=fonts['sm'].render(m["desc"],True,COL_TEXT_DIM); ds.set_alpha(a); screen.blit(ds,(x+80,y+62))

    def _draw_tooltip(self, screen, fonts, res):
        if res=="rival":
            d="The power of those who seek to usurp your throne. At 100, a Civil War erupts."; n="RIVAL THREAT"; v=int(self.display_rival_power); c=COL_ORANGE
        else:
            d=RES_DESC[res]; n=RES_NAME[res]; v=int(self.display_resources[res]); c=RES_COL[res]
        lines=[n,d,f"Current: {v}/100"]; mw=max(fonts['sm'].size(l)[0] for l in lines)+24; h=len(lines)*20+16
        mx,my=pygame.mouse.get_pos(); tx,ty=mx+16,my+16
        if tx+mw>WIDTH: tx=mx-mw-16
        if ty+h>HEIGHT: ty=my-h-16
        bg=pygame.Surface((mw,h),pygame.SRCALPHA); pygame.draw.rect(bg,(*COL_PANEL_DARK,230),bg.get_rect(),border_radius=8); pygame.draw.rect(bg,c,bg.get_rect(),width=2,border_radius=8)
        screen.blit(bg,(tx,ty))
        for i,l in enumerate(lines):
            col=c if i==0 else (COL_TEXT if i==1 else COL_TEXT_DIM)
            surf=fonts['sm'].render(l,True,col); screen.blit(surf,(tx+12,ty+8+i*20))

    def _draw_debug(self, screen, fonts):
        info=[f"FPS: {int(self.fps)}",f"State: {self.state.name}",f"Phase: {self.turn_phase.name}",
              f"Particles: {len(self.particles)}",f"Tweens: {len(self.tweens)}",f"Modifiers: {len(self.modifiers)}",
              f"Bonuses: {len(self.permanent_drifts)}",f"Rival: {self.rival_power}",f"Foreign: {self.foreign_relations}",
              f"Pop: {self.population:.1f}M",f"Turn: {self.turn}/{MAX_TURNS}",f"Diff: {self.difficulty}"]
        bg=pygame.Surface((200,len(info)*16+10),pygame.SRCALPHA); bg.fill((0,0,0,180)); screen.blit(bg,(10,160))
        for i,l in enumerate(info):
            surf=fonts['tiny'].render(l,True,COL_GREEN_BR); screen.blit(surf,(16,165+i*16))

def main():
    pygame.init()
    screen=pygame.display.set_mode((WIDTH,HEIGHT),pygame.SCALED,vsync=1)
    pygame.display.set_caption("STATECRAFT — Oracle & Ledger Edition")
    clock=pygame.time.Clock()
    fonts={
        'title':pygame.font.SysFont("georgia,timesnewroman,serif",72,bold=True),
        'hdr':pygame.font.SysFont("georgia,timesnewroman,serif",30,bold=True),
        'sub':pygame.font.SysFont("georgia,timesnewroman,serif",26,italic=True),
        'body':pygame.font.SysFont("arial,helvetica,sans-serif",20),
        'btn':pygame.font.SysFont("arial,helvetica,sans-serif",22,bold=True),
        'sm':pygame.font.SysFont("arial,helvetica,sans-serif",16),
        'tiny':pygame.font.SysFont("arial,helvetica,sans-serif",13),
        'card':pygame.font.SysFont("georgia,timesnewroman,serif",26,bold=True),
        'res':pygame.font.SysFont("arial,helvetica,sans-serif",28,bold=True),
        'float':pygame.font.SysFont("arial,helvetica,sans-serif",26,bold=True)
    }
    sound=SoundManager(); game=Game(screen,sound); running=True
    while running:
        dt=min(clock.tick(FPS)/1000.0,1/30)
        for e in pygame.event.get():
            if e.type==pygame.QUIT: running=False
            else: game.handle_event(e)
        game.update(dt, clock.get_fps()); game.draw(screen,fonts); pygame.display.flip()
    pygame.quit()

if __name__=="__main__": main()