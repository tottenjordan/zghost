#!/usr/bin/env python3
"""Generate a 4K GCP-branded System Architecture diagram."""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import os

# ── GCP Brand ──
BLUE, DKBLUE, DPBLUE = "#4285F4", "#1A73E8", "#174EA6"
RED, YELLOW, AMBER    = "#EA4335", "#FBBC04", "#E8A400"
GREEN, WHITE          = "#34A853", "#FFFFFF"
DARK, MED, LGRAY      = "#202124", "#5F6368", "#DADCE0"
BG                     = "#FAFBFC"
LT_BLUE, VLT_BLUE     = "#E8F0FE", "#F0F6FF"
LT_GREEN               = "#E6F4EA"

DPI = 192
fig, ax = plt.subplots(1, 1, figsize=(3840/DPI, 2160/DPI), dpi=DPI)
fig.patch.set_facecolor(BG)
ax.set_xlim(0, 100); ax.set_ylim(0, 56.25)
ax.set_aspect("equal"); ax.axis("off")
fig.subplots_adjust(left=0, right=1, top=1, bottom=0)

def rbox(x,y,w,h,fc,ec=None,lw=1.5,a=1,r=0.5,z=1):
    ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle=f"round,pad=0,rounding_size={r}",
        facecolor=fc,edgecolor=ec or fc,linewidth=lw,alpha=a,zorder=z))
def T(x,y,s,sz=6,c=DARK,w="normal",ha="center",va="center",z=10):
    ax.text(x,y,s,fontsize=sz,color=c,weight=w,ha=ha,va=va,zorder=z,fontfamily="sans-serif")
def C(cx,cy,r,fc,ec=WHITE,lw=1,z=5):
    ax.add_patch(plt.Circle((cx,cy),r,facecolor=fc,edgecolor=ec,linewidth=lw,zorder=z))
def badge(cx,cy,r,col,let,z=5,fs=5):
    C(cx,cy,r,col,z=z); T(cx,cy,let,sz=fs,c=WHITE,w="bold",z=z+1)
def arr(x1,y1,x2,y2,c=MED,lw=1.2,lab="",lo=(0,0.5),z=3,cs="arc3,rad=0"):
    ax.add_patch(FancyArrowPatch((x1,y1),(x2,y2),arrowstyle="-|>",color=c,
        lw=lw,zorder=z,connectionstyle=cs,mutation_scale=13))
    if lab:
        mx,my=(x1+x2)/2+lo[0],(y1+y2)/2+lo[1]
        pw=len(lab)*0.46+0.6
        rbox(mx-pw/2,my-0.4,pw,0.8,WHITE,WHITE,lw=0,a=0.93,r=0.2,z=z+1)
        T(mx,my,lab,sz=4.5,c=c,w="bold",z=z+2)

# ╔══════════════════════════════════════════╗
# ║  TITLE BAR                              ║
# ╚══════════════════════════════════════════╝
rbox(0,53.5,100,2.75, DPBLUE,DPBLUE, lw=0,z=1,r=0)
T(50,55.2, "Marketing Intelligence \u2014 System Architecture", sz=10, c=WHITE, w="bold")
T(50,54.15, "v1.0 \u2014 March 2026", sz=5.5, c="#A8C7FA")

# ╔══════════════════════════════════════════╗
# ║  COL 1 — USER LAYER                     ║
# ╚══════════════════════════════════════════╝
T(11,52.5,"USER  LAYER",sz=5.5,c=BLUE,w="bold")

# person
px,py = 11, 49.8
C(px,py,0.85,BLUE,z=5)
C(px,py+0.28,0.2,WHITE,WHITE,0,z=6)
ax.add_patch(mpatches.Wedge((px,py-0.08),0.38,35,145,facecolor=WHITE,edgecolor=WHITE,lw=0,zorder=6))
T(px,py-1.5,"Marketing User",sz=5.5,c=DARK,w="bold")
arr(px,py-2.1,px,46.2, c=BLUE,lw=1.6,lab="HTTPS",lo=(1.8,0))

# frontend
FX,FY,FW,FH = 1.3,16,19.4,29.5
rbox(FX,FY,FW,FH, VLT_BLUE,BLUE, lw=2,z=2,r=0.7)
T(FX+FW/2,FY+FH-1.0,"React + Vite Frontend",sz=6.5,c=DKBLUE,w="bold")
T(FX+FW/2,FY+FH-2.2,"port 5173",sz=4.5,c=MED)

feats = [("Campaign Wizard",BLUE),("Pipeline Dashboard",GREEN),("AV Studio",RED),
         ("Narrative Editor",AMBER),("Voice Assistant",DKBLUE),("Results Gallery",GREEN)]
ch,cw,cx0=2.6,FW-2.2,FX+1.1
cs0 = FY+FH-4.3
for i,(lab,col) in enumerate(feats):
    cy=cs0-i*(ch+0.55)
    rbox(cx0,cy,cw,ch,WHITE,LGRAY,lw=1,z=4,r=0.35)
    rbox(cx0,cy,0.4,ch,col,col,lw=0,z=5,r=0.35)
    C(cx0+1.2,cy+ch/2,0.25,col,WHITE,0.6,z=6)
    T(cx0+cw/2+0.4,cy+ch/2,lab,sz=5,c=DARK,w="bold",z=6)

# ╔══════════════════════════════════════════╗
# ║  COL 2 — CLOUD RUN                      ║
# ╚══════════════════════════════════════════╝
C2X,C2W = 23.5, 27

# Compute needed height for services
SH,SG = 6.0, 0.65
n_svc = 5
needed = n_svc*SH + (n_svc-1)*SG + 5.5 + 1.5  # services + header + bottom pad
CRY = 52.5 - 1 - needed  # top edge minus margin
CRH = needed

rbox(C2X,CRY,C2W,CRH, LT_BLUE,DKBLUE, lw=2.5,z=1,r=0.9)
rbox(C2X+0.5,CRY+CRH-3.8,C2W-1,3.3, DKBLUE,DKBLUE, lw=0,z=3,r=0.6)
T(C2X+C2W/2,CRY+CRH-1.2,"Cloud Run \u2014 Single Service",sz=7,c=WHITE,w="bold",z=10)
T(C2X+C2W/2,CRY+CRH-2.7,"managed by supervisord",sz=4.8,c="#A8C7FA",z=10)

svcs = [
    ("nginx Reverse Proxy","port 8080","routes all traffic",        BLUE,"N"),
    ("API Server / FastAPI","port 8000","sessions, SSE streaming, export",GREEN,"A"),
    ("ADK Server","port 8001","agent orchestration runtime",        RED,"K"),
    ("Voice Server","port 8081","WebSocket, Gemini Live API",       AMBER,"V"),
    ("Memory Bank API","port 8082","Vertex AI Memory Bank",         DKBLUE,"M"),
]
SX,SW = C2X+1.5, C2W-3
SS = CRY+CRH-5.2
syc=[]
for i,(nm,pt,ds,cl,ic) in enumerate(svcs):
    sy=SS-i*(SH+SG); syc.append(sy+SH/2)
    rbox(SX,sy,SW,SH,WHITE,cl,lw=1.5,z=4,r=0.45)
    rbox(SX+0.3,sy+SH-0.32,SW-0.6,0.32,cl,cl,lw=0,z=5,r=0.18)
    badge(SX+1.4,sy+SH/2,0.75,cl,ic,z=6,fs=6)
    T(SX+3.1,sy+SH/2+1.1,nm,sz=5.8,c=DARK,w="bold",ha="left",z=6)
    T(SX+3.1,sy+SH/2-0.1,pt,sz=5,c=cl,w="bold",ha="left",z=6)
    T(SX+3.1,sy+SH/2-1.2,ds,sz=4.3,c=MED,ha="left",z=6)

# ╔══════════════════════════════════════════╗
# ║  COL 3 — GCP SERVICES                   ║
# ╚══════════════════════════════════════════╝
C3X,C3W = 54.5, 44
T(C3X+C3W/2,52.5,"GOOGLE  CLOUD  PLATFORM  SERVICES",sz=5.5,c=BLUE,w="bold")

# Vertex AI container
VX,VY,VW,VH = C3X+0.5,30,C3W-1,22
rbox(VX,VY,VW,VH,LT_GREEN,GREEN,lw=2,z=2,r=0.7)
rbox(VX+0.5,VY+VH-3.0,VW-1,2.5,GREEN,GREEN,lw=0,z=3,r=0.5)
C(VX+1.8,VY+VH-1.75,0.6,WHITE,WHITE,0,z=6)
T(VX+1.8,VY+VH-1.75,"V",sz=5,c=GREEN,w="bold",z=7)
T(VX+3.4,VY+VH-1.75,"Vertex AI",sz=7,c=WHITE,w="bold",ha="left",z=10)

models = [
    ("Gemini 2.5 Flash","agent reasoning, critique",BLUE,"G"),
    ("Gemini 2.5 Flash Image","image generation",BLUE,"I"),
    ("Veo 3.1 Fast","video generation, frame cond.",RED,"V"),
    ("Chirp 3 HD","voice-over, dialogue",AMBER,"C"),
    ("Lyria 2","soundtrack, sound effects",GREEN,"L"),
]
MH,MG=3.2,0.5; MCW=(VW-3)/2; MS=VY+VH-4.5
for i,(mn,md,mc,mi) in enumerate(models):
    if i<3: mx,row = VX+1.0, i
    else:   mx,row = VX+1.0+MCW+1.0, i-3
    my=MS-row*(MH+MG)
    rbox(mx,my,MCW,MH,WHITE,mc,lw=1.2,z=4,r=0.3)
    badge(mx+0.8,my+MH/2,0.5,mc,mi,z=6,fs=4)
    T(mx+1.9,my+MH/2+0.5,mn,sz=5,c=DARK,w="bold",ha="left",z=6)
    T(mx+1.9,my+MH/2-0.5,md,sz=4,c=MED,ha="left",z=6)

# Other services — 2 columns
gsvc=[
    ("Agent Engine","managed deployment, sessions",BLUE,"AE"),
    ("Cloud Storage","gs://zghost-media-center",GREEN,"CS"),
    ("BigQuery","Google Trends data warehouse",BLUE,"BQ"),
    ("Secret Manager","YouTube API keys",RED,"SM"),
    ("YouTube Data API v3","trending video discovery",RED,"YT"),
    ("Memory Bank Service","cross-session memory",GREEN,"MB"),
    ("OpenTelemetry","distributed tracing",AMBER,"OT"),
]
GH,GG=3.0,0.5; GCW=(C3W-2.5)/2; GS0=27.5
for i,(sn,sd,sc,si) in enumerate(gsvc):
    col,row=i%2,i//2
    gx=C3X+0.5+col*(GCW+1.5); gy=GS0-row*(GH+GG)
    rbox(gx,gy,GCW,GH,WHITE,sc,lw=1.2,z=4,r=0.35)
    badge(gx+0.9,gy+GH/2,0.5,sc,si,z=6,fs=3.5)
    T(gx+2.1,gy+GH/2+0.45,sn,sz=4.8,c=DARK,w="bold",ha="left",z=6)
    T(gx+2.1,gy+GH/2-0.45,sd,sz=3.8,c=MED,ha="left",z=6)

# ╔══════════════════════════════════════════╗
# ║  ARROWS                                 ║
# ╚══════════════════════════════════════════╝
CR_R = C2X+C2W

arr(FX+FW, FY+FH/2+4.5, C2X, syc[0], c=BLUE,lw=2,lab="HTTPS",lo=(0,0.6))
arr(CR_R, syc[1], VX, VY+VH/2+4, c=GREEN,lw=1.6,lab="gRPC",lo=(0,0.6))
arr(CR_R, syc[2], VX, VY+VH/2, c=RED,lw=1.6,lab="gRPC",lo=(0,0.6))
arr(CR_R, syc[3], VX, VY+VH/2-4, c=AMBER,lw=1.3,lab="WebSocket",lo=(0,0.6))
arr(CR_R, syc[4], C3X+0.5, GS0-2*(GH+GG)+GH/2, c=DKBLUE,lw=1.3,lab="REST",lo=(0,0.6))
arr(CR_R, syc[2]-1.5, C3X+0.5, GS0-0.5*(GH+GG)+GH/2,
    c=BLUE,lw=1.0,lab="SQL",lo=(2,0.6),cs="arc3,rad=0.15")

# ╔══════════════════════════════════════════╗
# ║  FOOTER                                 ║
# ╚══════════════════════════════════════════╝
fy=2.3
for dx,clr in [(0,BLUE),(0.55,RED),(1.1,YELLOW),(1.65,GREEN)]:
    C(3+dx,fy,0.16,clr,clr,0,z=5)
T(6,fy,"Google Cloud",sz=5.5,c=MED,w="bold",ha="left")

LX,LY=28,2.0
T(LX,LY+0.9,"Connection Types:",sz=4.5,c=DARK,w="bold",ha="left")
for lab,col,off in [("HTTPS",BLUE,0),("gRPC",GREEN,8),("REST",DKBLUE,16),("WebSocket",AMBER,25),("SQL",BLUE,36)]:
    lx=LX+off
    ax.annotate("",xy=(lx+2,LY),xytext=(lx,LY),arrowprops=dict(arrowstyle="-|>",color=col,lw=1.5),zorder=5)
    T(lx+2.8,LY,lab,sz=4.2,c=col,w="bold",ha="left")

T(96,fy,"Google Confidential",sz=4.5,c=LGRAY,ha="right")

# save
out="/usr/local/google/home/jwortz/zghost/docs/images/diagrams/system-architecture-4k.png"
fig.savefig(out,dpi=DPI,facecolor=BG,pad_inches=0)
plt.close(fig)
print(f"Saved: {out}")
from PIL import Image; img=Image.open(out)
print(f"Resolution: {img.size[0]}x{img.size[1]} px | Size: {os.path.getsize(out)/1024/1024:.1f} MB")
