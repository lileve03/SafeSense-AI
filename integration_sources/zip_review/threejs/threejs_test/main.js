import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";


// ======================================================
// 1. THREE.JS SCENE
// ======================================================

const scene = new THREE.Scene();
scene.background = new THREE.Color(0xf1f5f9);


const camera = new THREE.PerspectiveCamera(
    60,
    window.innerWidth / window.innerHeight,
    0.1,
    1000
);

camera.position.set(8, 6, 9);


const renderer = new THREE.WebGLRenderer({
    antialias: true
});

renderer.setSize(
    window.innerWidth,
    window.innerHeight
);

renderer.setPixelRatio(
    Math.min(
        window.devicePixelRatio,
        2
    )
);

renderer.shadowMap.enabled = true;

document.body.appendChild(
    renderer.domElement
);


// ======================================================
// 2. CONTROLS
// ======================================================

const controls = new OrbitControls(
    camera,
    renderer.domElement
);

controls.target.set(
    0,
    1,
    0
);

controls.enableDamping = true;


// ======================================================
// 3. LIGHT
// ======================================================

const ambientLight = new THREE.AmbientLight(
    0xffffff,
    2
);

scene.add(
    ambientLight
);


const directionalLight = new THREE.DirectionalLight(
    0xffffff,
    2
);

directionalLight.position.set(
    5,
    8,
    5
);

directionalLight.castShadow = true;

scene.add(
    directionalLight
);


// ======================================================
// 4. ROOM
// ======================================================

const floor = new THREE.Mesh(

    new THREE.PlaneGeometry(
        8,
        6
    ),

    new THREE.MeshStandardMaterial({
        color: 0xe8f3f1,
        side: THREE.DoubleSide
    })

);

floor.rotation.x = -Math.PI / 2;
floor.receiveShadow = true;

scene.add(
    floor
);


const grid = new THREE.GridHelper(
    8,
    16,
    0x7aa89f,
    0xcbd5d1
);

grid.position.y = 0.01;

scene.add(
    grid
);


function createWall(
    width,
    height,
    depth,
    x,
    y,
    z
) {

    const wall = new THREE.Mesh(

        new THREE.BoxGeometry(
            width,
            height,
            depth
        ),

        new THREE.MeshStandardMaterial({
            color: 0xffffff,
            transparent: true,
            opacity: 0.75
        })

    );

    wall.position.set(
        x,
        y,
        z
    );

    scene.add(
        wall
    );

    return wall;
}


const wallBack = createWall(
    8,
    3,
    0.08,
    0,
    1.5,
    -3
);


const wallLeft = createWall(
    0.08,
    3,
    6,
    -4,
    1.5,
    0
);


const wallRight = createWall(
    0.08,
    3,
    6,
    4,
    1.5,
    0
);


const roomObjects = [
    floor,
    grid,
    wallBack,
    wallLeft,
    wallRight
];


// ======================================================
// 5. mmWAVE RADAR
// ======================================================

const radarBody = new THREE.Mesh(

    new THREE.BoxGeometry(
        0.45,
        0.28,
        0.12
    ),

    new THREE.MeshStandardMaterial({
        color: 0x0f766e
    })

);

radarBody.position.set(
    0,
    2.4,
    -2.9
);

scene.add(
    radarBody
);


// ======================================================
// 6. RADAR SCAN RINGS
// ======================================================

const radarRings = [];


for (let i = 0; i < 3; i++) {

    const ring = new THREE.Mesh(

        new THREE.RingGeometry(
            0.3,
            0.34,
            64
        ),

        new THREE.MeshBasicMaterial({
            color: 0x14b8a6,
            transparent: true,
            opacity: 0.5,
            side: THREE.DoubleSide,
            depthWrite: false
        })

    );


    ring.rotation.x = -Math.PI / 2;


    ring.position.set(
        0,
        0.03,
        -2.2
    );


    scene.add(
        ring
    );


    radarRings.push(
        ring
    );
}


// ======================================================
// 7. CAMERA DEVICE
// ======================================================

const cameraDevice = new THREE.Group();


const cameraBody = new THREE.Mesh(

    new THREE.BoxGeometry(
        0.45,
        0.28,
        0.30
    ),

    new THREE.MeshStandardMaterial({
        color: 0x334155
    })

);


const cameraLens = new THREE.Mesh(

    new THREE.CylinderGeometry(
        0.09,
        0.09,
        0.15,
        24
    ),

    new THREE.MeshStandardMaterial({
        color: 0x0f172a
    })

);

cameraLens.rotation.x = Math.PI / 2;

cameraLens.position.z = 0.22;


cameraDevice.add(
    cameraBody,
    cameraLens
);


cameraDevice.position.set(
    0,
    2.4,
    -2.8
);

cameraDevice.visible = false;

scene.add(
    cameraDevice
);


// ======================================================
// 8. PERSON
// ======================================================

function createPerson(
    color
) {

    const person = new THREE.Group();


    const material = new THREE.MeshStandardMaterial({
        color
    });


    const head = new THREE.Mesh(

        new THREE.SphereGeometry(
            0.18,
            24,
            24
        ),

        material.clone()

    );

    head.position.y = 1.55;


    const body = new THREE.Mesh(

        new THREE.CapsuleGeometry(
            0.22,
            0.70,
            6,
            12
        ),

        material.clone()

    );

    body.position.y = 0.90;


    const leftLeg = new THREE.Mesh(

        new THREE.CylinderGeometry(
            0.07,
            0.07,
            0.60,
            12
        ),

        material.clone()

    );

    leftLeg.position.set(
        -0.11,
        0.30,
        0
    );


    const rightLeg = new THREE.Mesh(

        new THREE.CylinderGeometry(
            0.07,
            0.07,
            0.60,
            12
        ),

        material.clone()

    );

    rightLeg.position.set(
        0.11,
        0.30,
        0
    );


    person.add(
        head,
        body,
        leftLeg,
        rightLeg
    );


    return person;
}


// ======================================================
// 9. PEOPLE
// ======================================================

const person1 = createPerson(
    0x22c55e
);

person1.position.set(
    -2,
    0,
    0.4
);

scene.add(
    person1
);


const person2 = createPerson(
    0x22c55e
);

person2.position.set(
    2,
    0,
    0.7
);

scene.add(
    person2
);


// ======================================================
// 10. HEATMAP
// ======================================================

const heatmapMaterial = new THREE.MeshBasicMaterial({
    color: 0x22c55e,
    transparent: true,
    opacity: 0.14,
    side: THREE.DoubleSide,
    depthWrite: false
});


const riskHeatmap = new THREE.Mesh(

    new THREE.CircleGeometry(
        1.2,
        64
    ),

    heatmapMaterial

);

riskHeatmap.rotation.x = -Math.PI / 2;
riskHeatmap.position.y = 0.04;

scene.add(
    riskHeatmap
);


// ======================================================
// 11. DISTANCE LINE
// ======================================================

const distanceLine = new THREE.Line(

    new THREE.BufferGeometry(),

    new THREE.LineBasicMaterial({
        color: 0x22c55e
    })

);

scene.add(
    distanceLine
);


function updateDistanceLine() {

    const point1 = new THREE.Vector3(
        person1.position.x,
        0.8,
        person1.position.z
    );


    const point2 = new THREE.Vector3(
        person2.position.x,
        0.8,
        person2.position.z
    );


    distanceLine.geometry.setFromPoints([
        point1,
        point2
    ]);
}


// ======================================================
// 12. DISTANCE LABEL
// ======================================================

function createTextSprite(
    text
) {

    const canvas = document.createElement(
        "canvas"
    );

    canvas.width = 320;
    canvas.height = 140;


    const context = canvas.getContext(
        "2d"
    );


    const texture = new THREE.CanvasTexture(
        canvas
    );


    const sprite = new THREE.Sprite(

        new THREE.SpriteMaterial({
            map: texture,
            transparent: true
        })

    );


    sprite.scale.set(
        2,
        0.9,
        1
    );


    sprite.userData.canvas = canvas;
    sprite.userData.context = context;
    sprite.userData.texture = texture;


    updateSpriteText(
        sprite,
        text
    );


    return sprite;
}


function updateSpriteText(
    sprite,
    text
) {

    const canvas = sprite.userData.canvas;

    const context = sprite.userData.context;


    context.clearRect(
        0,
        0,
        canvas.width,
        canvas.height
    );


    context.fillStyle =
        "rgba(255,255,255,0.95)";


    context.fillRect(
        0,
        0,
        canvas.width,
        canvas.height
    );


    context.font =
        "bold 42px Arial";


    context.fillStyle =
        "#111827";


    context.textAlign =
        "center";


    context.textBaseline =
        "middle";


    context.fillText(
        text,
        canvas.width / 2,
        canvas.height / 2
    );


    sprite.userData.texture.needsUpdate =
        true;
}


const distanceLabel = createTextSprite(
    "4.00 m"
);

scene.add(
    distanceLabel
);


// ======================================================
// 13. CSS
// ======================================================

const uiStyle = document.createElement(
    "style"
);


uiStyle.textContent = `

* {
    box-sizing:border-box;
}

body {
    font-family:Arial,sans-serif;
}

.hud-row {
    display:flex;
    justify-content:space-between;
    gap:16px;
    margin-top:10px;
    font-size:13px;
    color:#475569;
}

.hud-row strong {
    color:#0f172a;
}

.zone-button {
    display:block;
    width:100%;
    padding:10px 12px;
    margin-top:7px;
    border:1px solid #e2e8f0;
    border-radius:9px;
    background:white;
    color:#334155;
    font-size:12px;
    font-weight:700;
    cursor:pointer;
    text-align:left;
}

.zone-button.active {
    background:#ccfbf1;
    border-color:#14b8a6;
    color:#0f766e;
}

.action-button {
    border:none;
    border-radius:8px;
    padding:8px 12px;
    font-size:11px;
    font-weight:700;
    cursor:pointer;
}

.overview-zone-card {
    background:white;
    border:1px solid #e2e8f0;
    border-radius:14px;
    padding:16px;
    cursor:pointer;
    transition:0.15s;
}

.overview-zone-card:hover {
    transform:translateY(-2px);
    box-shadow:0 10px 24px rgba(15,23,42,0.08);
}

.notification-item {
    padding:10px 0;
    border-bottom:1px solid #e2e8f0;
}

`;


document.head.appendChild(
    uiStyle
);


// ======================================================
// 14. ZONE CONFIGURATION
// ======================================================

const zoneConfig = {

    TOILET: {

        name:
            "Toilet Block B",

        sensor:
            "mmWave + SOS",

        privacy:
            "Privacy-sensitive • No camera",

        device:
            "RADAR",

        responder:
            "Security Team A",

        baseETA:
            90,

        status:
            "NORMAL",

        responseStatus:
            "STANDBY",

        eta:
            0

    },


    CORRIDOR: {

        name:
            "Corridor A",

        sensor:
            "Camera AI",

        privacy:
            "Camera-permitted",

        device:
            "CAMERA",

        responder:
            "Teacher on Duty",

        baseETA:
            60,

        status:
            "NORMAL",

        responseStatus:
            "STANDBY",

        eta:
            0

    },


    STAIRCASE: {

        name:
            "Staircase C",

        sensor:
            "Camera + Fall Detection",

        privacy:
            "Camera-permitted",

        device:
            "CAMERA",

        responder:
            "Safety Officer",

        baseETA:
            75,

        status:
            "NORMAL",

        responseStatus:
            "STANDBY",

        eta:
            0

    }

};


// ======================================================
// 15. GLOBAL STATE
// ======================================================

let viewMode =
    "OVERVIEW";


let currentZone =
    "TOILET";


let simulationTime =
    0;


let previousPosition1 =
    person1.position.clone();


let previousPosition2 =
    person2.position.clone();


let closeContactStartTime =
    null;


let closeContactDuration =
    0;


let fallDetected =
    false;


let sosActive =
    false;


let currentEventType =
    "NORMAL";


let responseTimer =
    null;


let notificationCounter =
    0;


// ======================================================
// 16. SCHOOL OVERVIEW
// ======================================================

const overviewPanel = document.createElement(
    "div"
);


Object.assign(
    overviewPanel.style,
    {
        position:
            "absolute",

        top:
            "50%",

        left:
            "50%",

        transform:
            "translate(-50%, -50%)",

        width:
            "820px",

        padding:
            "26px",

        background:
            "rgba(248,250,252,0.98)",

        border:
            "1px solid #e2e8f0",

        borderRadius:
            "22px",

        boxShadow:
            "0 25px 70px rgba(15,23,42,0.16)",

        zIndex:
            "100"
    }
);


overviewPanel.innerHTML = `

<div style="
    display:flex;
    justify-content:space-between;
    align-items:flex-start;
">

    <div>

        <div style="
            font-size:11px;
            font-weight:800;
            letter-spacing:1.5px;
            color:#0f766e;
        ">
            AI SCHOOL SAFETY
        </div>

        <div style="
            font-size:28px;
            font-weight:800;
            color:#0f172a;
            margin-top:5px;
        ">
            School Digital Twin
        </div>

        <div style="
            font-size:12px;
            color:#64748b;
            margin-top:6px;
        ">
            Privacy-aware multi-zone safety monitoring
        </div>

    </div>


    <div style="
        text-align:right;
    ">

        <div style="
            font-size:10px;
            font-weight:700;
            color:#94a3b8;
        ">
            SCHOOL STATUS
        </div>

        <div
            id="overviewSchoolStatus"
            style="
                display:inline-block;
                margin-top:6px;
                padding:7px 12px;
                border-radius:999px;
                background:#dcfce7;
                color:#15803d;
                font-size:11px;
                font-weight:800;
            "
        >
            NORMAL
        </div>

    </div>

</div>


<div style="
    margin-top:22px;
    display:grid;
    grid-template-columns:repeat(3,1fr);
    gap:14px;
">

    ${createOverviewZoneHTML(
        "overviewToilet",
        "PRIVACY ZONE",
        "Toilet Block B",
        "mmWave + SOS",
        "overviewToiletStatus",
        "overviewToiletResponse"
    )}


    ${createOverviewZoneHTML(
        "overviewCorridor",
        "CAMERA ZONE",
        "Corridor A",
        "Camera AI",
        "overviewCorridorStatus",
        "overviewCorridorResponse"
    )}


    ${createOverviewZoneHTML(
        "overviewStaircase",
        "CAMERA ZONE",
        "Staircase C",
        "Camera + Fall Detection",
        "overviewStaircaseStatus",
        "overviewStaircaseResponse"
    )}

</div>


<div style="
    margin-top:18px;
    border-top:1px solid #e2e8f0;
    padding-top:14px;
    font-size:11px;
    color:#64748b;
">
    Select a zone to inspect its live digital twin and response status.
</div>

`;


document.body.appendChild(
    overviewPanel
);


function createOverviewZoneHTML(
    cardID,
    type,
    name,
    sensor,
    statusID,
    responseID
) {

    return `

    <div
        id="${cardID}"
        class="overview-zone-card"
    >

        <div style="
            font-size:10px;
            color:#64748b;
            font-weight:700;
        ">
            ${type}
        </div>


        <div style="
            font-size:17px;
            font-weight:800;
            color:#0f172a;
            margin-top:6px;
        ">
            ${name}
        </div>


        <div style="
            margin-top:6px;
            font-size:11px;
            color:#64748b;
            min-height:28px;
        ">
            ${sensor}
        </div>


        <div
            id="${statusID}"
            style="
                display:inline-block;
                margin-top:12px;
                padding:6px 10px;
                border-radius:999px;
                background:#dcfce7;
                color:#15803d;
                font-size:10px;
                font-weight:800;
            "
        >
            NORMAL
        </div>


        <div
            id="${responseID}"
            style="
                margin-top:12px;
                font-size:11px;
                color:#64748b;
                line-height:1.5;
            "
        >
            Response: Standby
        </div>

    </div>

    `;
}


// ======================================================
// 17. DETAIL LEFT PANEL
// ======================================================

const detailHeader = document.createElement(
    "div"
);


Object.assign(
    detailHeader.style,
    {
        position:
            "absolute",

        top:
            "24px",

        left:
            "24px",

        width:
            "235px",

        padding:
            "16px",

        background:
            "rgba(255,255,255,0.96)",

        border:
            "1px solid #dbe2ea",

        borderRadius:
            "16px",

        boxShadow:
            "0 12px 30px rgba(15,23,42,0.12)",

        zIndex:
            "20",

        display:
            "none"
    }
);


detailHeader.innerHTML = `

<button
    id="backOverview"
    style="
        border:none;
        background:#f1f5f9;
        color:#334155;
        border-radius:8px;
        padding:7px 10px;
        font-weight:700;
        font-size:11px;
        cursor:pointer;
        margin-bottom:12px;
    "
>
    ← School Overview
</button>


<div style="
    font-size:10px;
    font-weight:800;
    letter-spacing:1px;
    color:#64748b;
">
    SELECTED ZONE
</div>


<div
    id="detailZoneName"
    style="
        margin-top:7px;
        font-size:17px;
        font-weight:800;
        color:#0f172a;
    "
>
</div>


<div
    id="detailSensor"
    style="
        margin-top:7px;
        font-size:12px;
        font-weight:700;
        color:#0f766e;
    "
>
</div>


<div
    id="detailPrivacy"
    style="
        margin-top:4px;
        font-size:11px;
        color:#64748b;
    "
>
</div>


<div style="
    border-top:1px solid #e2e8f0;
    margin-top:12px;
    padding-top:10px;
">

    <button
        id="detailToilet"
        class="zone-button"
    >
        Toilet Block B
    </button>


    <button
        id="detailCorridor"
        class="zone-button"
    >
        Corridor A
    </button>


    <button
        id="detailStaircase"
        class="zone-button"
    >
        Staircase C
    </button>

</div>

`;


document.body.appendChild(
    detailHeader
);


// ======================================================
// 18. HUD
// ======================================================

const hud = document.createElement(
    "div"
);


Object.assign(
    hud.style,
    {
        position:
            "absolute",

        top:
            "24px",

        right:
            "24px",

        width:
            "320px",

        padding:
            "18px",

        background:
            "rgba(255,255,255,0.96)",

        borderRadius:
            "16px",

        border:
            "1px solid #dbe2ea",

        boxShadow:
            "0 12px 30px rgba(15,23,42,0.12)",

        zIndex:
            "20",

        display:
            "none"
    }
);


hud.innerHTML = `

<div
    id="hudZoneName"
    style="
        font-size:11px;
        font-weight:800;
        color:#0f766e;
    "
>
</div>


<div style="
    font-size:12px;
    font-weight:700;
    letter-spacing:1px;
    color:#64748b;
    margin-top:5px;
">
    LIVE SENSOR METRICS
</div>


<div class="hud-row">
    <span>People</span>
    <strong>2</strong>
</div>


<div class="hud-row">
    <span>Distance</span>
    <strong id="hudDistance">
        0.00 m
    </strong>
</div>


<div class="hud-row">
    <span>Motion</span>
    <strong id="hudMotion">
        0%
    </strong>
</div>


<div class="hud-row">
    <span>Close Contact</span>
    <strong id="hudDuration">
        0.0 s
    </strong>
</div>


<div class="hud-row">
    <span>Fall</span>
    <strong id="hudFall">
        No
    </strong>
</div>


<div style="
    border-top:1px solid #e2e8f0;
    margin-top:14px;
    padding-top:14px;
">

    <div style="
        font-size:11px;
        font-weight:700;
        color:#64748b;
    ">
        AI INTERACTION RISK
    </div>


    <div style="
        display:flex;
        justify-content:space-between;
        align-items:flex-end;
        margin-top:5px;
    ">

        <div
            id="hudRisk"
            style="
                font-size:36px;
                font-weight:800;
            "
        >
            0
        </div>


        <div
            id="hudInteractionStatus"
            style="
                padding:6px 10px;
                border-radius:999px;
                background:#dcfce7;
                color:#15803d;
                font-size:10px;
                font-weight:800;
            "
        >
            NORMAL
        </div>

    </div>

</div>


<div style="
    border-top:1px solid #e2e8f0;
    margin-top:14px;
    padding-top:14px;
">

    <div style="
        font-size:11px;
        font-weight:700;
        color:#64748b;
    ">
        ACTIVE EVENT
    </div>


    <div style="
        display:flex;
        justify-content:space-between;
        align-items:center;
        margin-top:8px;
    ">

        <strong
            id="hudEventType"
            style="
                font-size:13px;
            "
        >
            NONE
        </strong>


        <div
            id="hudEventPriority"
            style="
                padding:6px 10px;
                border-radius:999px;
                background:#f1f5f9;
                color:#64748b;
                font-size:10px;
                font-weight:800;
            "
        >
            MONITOR
        </div>

    </div>

</div>


<div style="
    border-top:1px solid #e2e8f0;
    margin-top:14px;
    padding-top:14px;
">

    <div style="
        font-size:11px;
        font-weight:700;
        color:#64748b;
    ">
        RESPONSE STATUS
    </div>


    <div class="hud-row">
        <span>Responder</span>
        <strong id="hudResponder">
            -
        </strong>
    </div>


    <div class="hud-row">
        <span>Status</span>
        <strong id="hudResponseStatus">
            STANDBY
        </strong>
    </div>


    <div class="hud-row">
        <span>ETA</span>

        <strong
            id="hudETA"
            style="
                font-size:17px;
            "
        >
            --
        </strong>
    </div>

</div>

`;


document.body.appendChild(
    hud
);


// ======================================================
// 19. SOS BUTTON
// ======================================================

const sosButton = document.createElement(
    "button"
);


sosButton.textContent =
    "SOS EMERGENCY";


Object.assign(
    sosButton.style,
    {
        position:
            "absolute",

        right:
            "24px",

        bottom:
            "24px",

        padding:
            "14px 22px",

        border:
            "none",

        borderRadius:
            "12px",

        background:
            "#dc2626",

        color:
            "white",

        fontWeight:
            "800",

        fontSize:
            "13px",

        cursor:
            "pointer",

        boxShadow:
            "0 10px 25px rgba(220,38,38,0.25)",

        zIndex:
            "30",

        display:
            "none"
    }
);


document.body.appendChild(
    sosButton
);


// ======================================================
// 20. EVENT CARD
// ======================================================

const eventCard = document.createElement(
    "div"
);


Object.assign(
    eventCard.style,
    {
        position:
            "absolute",

        top:
            "24px",

        left:
            "50%",

        transform:
            "translateX(-50%)",

        minWidth:
            "500px",

        padding:
            "18px",

        background:
            "white",

        borderRadius:
            "14px",

        boxShadow:
            "0 12px 30px rgba(15,23,42,0.15)",

        border:
            "1px solid #e2e8f0",

        display:
            "none",

        zIndex:
            "40"
    }
);


eventCard.innerHTML = `

<div
    id="eventTitle"
    style="
        font-size:14px;
        font-weight:800;
    "
>
</div>


<div
    id="eventDescription"
    style="
        margin-top:5px;
        color:#475569;
        font-size:12px;
    "
>
</div>


<div
    id="eventPriority"
    style="
        margin-top:8px;
        font-size:11px;
        font-weight:800;
    "
>
</div>


<div
    id="eventActions"
    style="
        margin-top:12px;
        display:flex;
        gap:8px;
        flex-wrap:wrap;
    "
>
</div>

`;


document.body.appendChild(
    eventCard
);


// ======================================================
// 21. EVENT LOG
// ======================================================

const timeline = document.createElement(
    "div"
);


Object.assign(
    timeline.style,
    {
        position:
            "absolute",

        left:
            "24px",

        bottom:
            "24px",

        width:
            "430px",

        padding:
            "18px",

        background:
            "rgba(255,255,255,0.95)",

        borderRadius:
            "16px",

        boxShadow:
            "0 12px 30px rgba(15,23,42,0.12)",

        zIndex:
            "20",

        display:
            "none"
    }
);


timeline.innerHTML = `

<div style="
    font-size:12px;
    font-weight:700;
    letter-spacing:1px;
    color:#64748b;
    margin-bottom:12px;
">
    EVENT & RESPONSE LOG
</div>


<div
    id="eventLog"
    style="
        max-height:220px;
        overflow-y:auto;
    "
>

    <div
        id="emptyLog"
        style="
            font-size:13px;
            color:#94a3b8;
        "
    >
        No events recorded
    </div>

</div>

`;


document.body.appendChild(
    timeline
);


// ======================================================
// 22. MOBILE TEACHER ALERT
// ======================================================

const mobileAlert = document.createElement(
    "div"
);


Object.assign(
    mobileAlert.style,
    {
        position:
            "absolute",

        right:
            "365px",

        bottom:
            "24px",

        width:
            "280px",

        background:
            "#0f172a",

        color:
            "white",

        borderRadius:
            "22px",

        padding:
            "14px",

        boxShadow:
            "0 18px 50px rgba(15,23,42,0.35)",

        zIndex:
            "80",

        display:
            "none"
    }
);


mobileAlert.innerHTML = `

<div style="
    width:60px;
    height:5px;
    border-radius:10px;
    background:#475569;
    margin:0 auto 13px auto;
">
</div>


<div style="
    font-size:10px;
    font-weight:800;
    color:#94a3b8;
">
    📱 TEACHER MOBILE ALERT
</div>


<div
    id="mobileAlertTitle"
    style="
        margin-top:9px;
        font-size:15px;
        font-weight:800;
    "
>
</div>


<div
    id="mobileAlertZone"
    style="
        margin-top:5px;
        font-size:12px;
        color:#cbd5e1;
    "
>
</div>


<div
    id="mobileAlertMessage"
    style="
        margin-top:10px;
        font-size:12px;
        line-height:1.5;
        color:#e2e8f0;
    "
>
</div>


<div style="
    border-top:1px solid #334155;
    margin-top:12px;
    padding-top:10px;
">

    <div style="
        font-size:10px;
        color:#94a3b8;
    ">
        RESPONDER
    </div>


    <div
        id="mobileResponder"
        style="
            margin-top:3px;
            font-size:12px;
            font-weight:700;
        "
    >
    </div>


    <div style="
        display:flex;
        justify-content:space-between;
        margin-top:10px;
    ">

        <span style="
            font-size:11px;
            color:#94a3b8;
        ">
            ETA
        </span>


        <strong
            id="mobileETA"
            style="
                font-size:17px;
            "
        >
            --
        </strong>

    </div>

</div>


<button
    id="mobileOpenIncident"
    style="
        width:100%;
        border:none;
        border-radius:9px;
        margin-top:12px;
        padding:9px;
        background:#2563eb;
        color:white;
        font-weight:800;
        cursor:pointer;
    "
>
    OPEN INCIDENT
</button>

`;


document.body.appendChild(
    mobileAlert
);


// ======================================================
// 23. NOTIFICATION CENTER
// ======================================================

const notificationPanel = document.createElement(
    "div"
);


Object.assign(
    notificationPanel.style,
    {
        position:
            "absolute",

        top:
            "24px",

        right:
            "365px",

        width:
            "270px",

        padding:
            "15px",

        background:
            "rgba(255,255,255,0.96)",

        border:
            "1px solid #e2e8f0",

        borderRadius:
            "14px",

        boxShadow:
            "0 12px 30px rgba(15,23,42,0.12)",

        zIndex:
            "20",

        display:
            "none"
    }
);


notificationPanel.innerHTML = `

<div style="
    display:flex;
    justify-content:space-between;
">

    <div style="
        font-size:11px;
        font-weight:800;
        letter-spacing:1px;
        color:#64748b;
    ">
        NOTIFICATIONS
    </div>


    <div
        id="notificationCount"
        style="
            min-width:20px;
            height:20px;
            border-radius:10px;
            background:#dc2626;
            color:white;
            font-size:10px;
            font-weight:800;
            display:flex;
            align-items:center;
            justify-content:center;
        "
    >
        0
    </div>

</div>


<div
    id="notificationList"
    style="
        max-height:130px;
        overflow-y:auto;
        margin-top:7px;
    "
>

    <div
        id="notificationEmpty"
        style="
            font-size:11px;
            color:#94a3b8;
            margin-top:8px;
        "
    >
        No notifications
    </div>

</div>

`;


document.body.appendChild(
    notificationPanel
);


// ======================================================
// 24. HELPER - LOG
// ======================================================

function logEvent(
    message
) {

    const log = document.getElementById(
        "eventLog"
    );


    const empty = document.getElementById(
        "emptyLog"
    );


    if (empty) {

        empty.remove();

    }


    const item = document.createElement(
        "div"
    );


    item.style.padding =
        "9px 0";


    item.style.borderBottom =
        "1px solid #e2e8f0";


    item.innerHTML = `

        <strong style="
            font-size:12px;
            color:#334155;
        ">
            ${message}
        </strong>

        <span style="
            float:right;
            color:#94a3b8;
            font-size:11px;
        ">
            ${new Date().toLocaleTimeString()}
        </span>

    `;


    log.prepend(
        item
    );
}


// ======================================================
// 25. NOTIFICATION FUNCTION
// ======================================================

function addNotification(
    title,
    message
) {

    notificationCounter++;


    document.getElementById(
        "notificationCount"
    ).textContent =
        notificationCounter;


    const list =
        document.getElementById(
            "notificationList"
        );


    const empty =
        document.getElementById(
            "notificationEmpty"
        );


    if (empty) {

        empty.remove();

    }


    const item =
        document.createElement(
            "div"
        );


    item.className =
        "notification-item";


    item.innerHTML = `

        <div style="
            font-size:11px;
            font-weight:800;
            color:#0f172a;
        ">
            ${title}
        </div>

        <div style="
            margin-top:3px;
            font-size:10px;
            color:#64748b;
            line-height:1.4;
        ">
            ${message}
        </div>

        <div style="
            margin-top:4px;
            font-size:9px;
            color:#94a3b8;
        ">
            ${new Date().toLocaleTimeString()}
        </div>

    `;


    list.prepend(
        item
    );
}


// ======================================================
// 26. MOBILE ALERT
// ======================================================

function showMobileAlert(
    event,
    zone
) {

    const config =
        zoneConfig[
            zone
        ];


    let title =
        "Safety Alert";


    let message =
        "Safety event requires attention.";


    if (
        event.type ===
        "SOS"
    ) {

        title =
            "🔴 CRITICAL SOS";


        message =
            "Student SOS manually activated. Immediate response required.";

    }


    else if (
        event.type ===
        "POSSIBLE_FALL"
    ) {

        title =
            "🟠 Possible Fall";


        message =
            "Possible fall detected. Please check occupant status.";

    }


    else if (
        event.type ===
        "INTERACTION_ANOMALY"
    ) {

        title =
            "🟡 Interaction Alert";


        message =
            "Unusual close-contact movement verified for intervention.";

    }


    document.getElementById(
        "mobileAlertTitle"
    ).textContent =
        title;


    document.getElementById(
        "mobileAlertZone"
    ).textContent =
        config.name;


    document.getElementById(
        "mobileAlertMessage"
    ).textContent =
        message;


    document.getElementById(
        "mobileResponder"
    ).textContent =
        config.responder;


    mobileAlert.style.display =
        "block";


    addNotification(
        title,
        config.name +
        " • " +
        config.responder +
        " notified"
    );


    logEvent(
        "Mobile alert sent to " +
        config.responder
    );
}


// ======================================================
// 27. ETA FORMAT
// ======================================================

function formatETA(
    seconds
) {

    if (
        seconds <=
        0
    ) {

        return "00:00";

    }


    const minutes =
        Math.floor(
            seconds /
            60
        );


    const secs =
        seconds %
        60;


    return String(
        minutes
    ).padStart(
        2,
        "0"
    )
    +
    ":"
    +
    String(
        secs
    ).padStart(
        2,
        "0"
    );
}


// ======================================================
// 28. RESPONSE / DISPATCH
// ======================================================

function dispatchResponder(
    event
) {

    const config =
        zoneConfig[
            currentZone
        ];


    if (
        config.responseStatus ===
        "EN_ROUTE"
    ) {

        return;

    }


    if (
        responseTimer
    ) {

        clearInterval(
            responseTimer
        );

    }


    config.responseStatus =
        "EN_ROUTE";


    config.eta =
        config.baseETA;


    showMobileAlert(
        event,
        currentZone
    );


    logEvent(
        config.responder +
        " dispatched"
    );


    updateResponseUI();


    responseTimer =
        setInterval(
            () => {

                if (
                    config.responseStatus !==
                    "EN_ROUTE"
                ) {

                    clearInterval(
                        responseTimer
                    );

                    responseTimer =
                        null;

                    return;

                }


                config.eta--;


                if (
                    config.eta <=
                    0
                ) {

                    config.eta =
                        0;


                    config.responseStatus =
                        "ARRIVED";


                    clearInterval(
                        responseTimer
                    );


                    responseTimer =
                        null;


                    logEvent(
                        config.responder +
                        " arrived at " +
                        config.name
                    );


                    addNotification(
                        "Responder Arrived",
                        config.responder +
                        " arrived at " +
                        config.name
                    );

                }


                updateResponseUI();

            },

            1000
        );
}


// ======================================================
// 29. MARK ARRIVED
// ======================================================

function markResponderArrived() {

    const config =
        zoneConfig[
            currentZone
        ];


    if (
        responseTimer
    ) {

        clearInterval(
            responseTimer
        );

        responseTimer =
            null;

    }


    config.eta =
        0;


    config.responseStatus =
        "ARRIVED";


    logEvent(
        config.responder +
        " marked ARRIVED"
    );


    addNotification(
        "Responder Arrived",
        config.responder +
        " is now at " +
        config.name
    );


    updateResponseUI();
}


// ======================================================
// 30. RESOLVE INCIDENT
// ======================================================

function resolveIncident() {

    const config =
        zoneConfig[
            currentZone
        ];


    if (
        responseTimer
    ) {

        clearInterval(
            responseTimer
        );

        responseTimer =
            null;

    }


    config.status =
        "NORMAL";


    config.responseStatus =
        "RESOLVED";


    config.eta =
        0;


    if (
        currentZone ===
        "TOILET"
    ) {

        sosActive =
            false;


        sosButton.textContent =
            "SOS EMERGENCY";


        sosButton.style.background =
            "#dc2626";

    }


    currentEventType =
        "NORMAL";


    eventCard.style.display =
        "none";


    mobileAlert.style.display =
        "none";


    logEvent(
        "Incident resolved • " +
        config.name
    );


    addNotification(
        "Incident Resolved",
        config.name +
        " returned to normal monitoring"
    );


    updateOverviewUI();


    updateResponseUI();
}


// ======================================================
// 31. RESPONSE UI
// ======================================================

function updateResponseUI() {

    const config =
        zoneConfig[
            currentZone
        ];


    document.getElementById(
        "hudResponder"
    ).textContent =
        config.responder;


    document.getElementById(
        "hudResponseStatus"
    ).textContent =
        config.responseStatus;


    let etaText =
        "--";


    if (
        config.responseStatus ===
        "EN_ROUTE"
    ) {

        etaText =
            formatETA(
                config.eta
            );

    }


    else if (
        config.responseStatus ===
        "ARRIVED"
    ) {

        etaText =
            "ARRIVED";

    }


    else if (
        config.responseStatus ===
        "RESOLVED"
    ) {

        etaText =
            "DONE";

    }


    document.getElementById(
        "hudETA"
    ).textContent =
        etaText;


    if (
        mobileAlert.style.display !==
        "none"
    ) {

        document.getElementById(
            "mobileETA"
        ).textContent =
            config.responseStatus ===
            "EN_ROUTE"
                ? formatETA(
                    config.eta
                )
                : config.responseStatus;

    }


    updateOverviewUI();
}


// ======================================================
// 32. OVERVIEW STATUS
// ======================================================

function setBadge(
    element,
    status
) {

    element.textContent =
        status;


    if (
        status ===
        "NORMAL"
    ) {

        element.style.background =
            "#dcfce7";

        element.style.color =
            "#15803d";

    }


    else if (
        status ===
        "VERIFY"
    ) {

        element.style.background =
            "#fef9c3";

        element.style.color =
            "#a16207";

    }


    else if (
        status ===
        "HIGH"
    ) {

        element.style.background =
            "#ffedd5";

        element.style.color =
            "#c2410c";

    }


    else {

        element.style.background =
            "#fee2e2";

        element.style.color =
            "#b91c1c";

    }
}


// ======================================================
// 33. OVERVIEW UI
// ======================================================

function updateOverviewUI() {

    setBadge(
        document.getElementById(
            "overviewToiletStatus"
        ),
        zoneConfig.TOILET.status
    );


    setBadge(
        document.getElementById(
            "overviewCorridorStatus"
        ),
        zoneConfig.CORRIDOR.status
    );


    setBadge(
        document.getElementById(
            "overviewStaircaseStatus"
        ),
        zoneConfig.STAIRCASE.status
    );


    updateOverviewResponse(
        "overviewToiletResponse",
        zoneConfig.TOILET
    );


    updateOverviewResponse(
        "overviewCorridorResponse",
        zoneConfig.CORRIDOR
    );


    updateOverviewResponse(
        "overviewStaircaseResponse",
        zoneConfig.STAIRCASE
    );


    const statuses = [

        zoneConfig.TOILET.status,

        zoneConfig.CORRIDOR.status,

        zoneConfig.STAIRCASE.status

    ];


    let schoolStatus =
        "NORMAL";


    if (
        statuses.includes(
            "CRITICAL"
        )
    ) {

        schoolStatus =
            "CRITICAL";

    }


    else if (
        statuses.includes(
            "HIGH"
        )
    ) {

        schoolStatus =
            "HIGH";

    }


    else if (
        statuses.includes(
            "VERIFY"
        )
    ) {

        schoolStatus =
            "VERIFY";

    }


    setBadge(
        document.getElementById(
            "overviewSchoolStatus"
        ),
        schoolStatus
    );
}


function updateOverviewResponse(
    id,
    config
) {

    const element =
        document.getElementById(
            id
        );


    if (
        config.responseStatus ===
        "EN_ROUTE"
    ) {

        element.innerHTML = `

            <strong>
                ${config.responder}
            </strong>

            <br>

            EN ROUTE • ETA
            ${formatETA(config.eta)}

        `;

    }


    else if (
        config.responseStatus ===
        "ARRIVED"
    ) {

        element.innerHTML = `

            <strong>
                ${config.responder}
            </strong>

            <br>

            ARRIVED

        `;

    }


    else if (
        config.responseStatus ===
        "RESOLVED"
    ) {

        element.innerHTML =
            "Response: Incident resolved";

    }


    else {

        element.innerHTML =
            "Response: Standby";

    }
}


// ======================================================
// 34. OVERVIEW / DETAIL
// ======================================================

function showOverview() {

    viewMode =
        "OVERVIEW";


    overviewPanel.style.display =
        "block";


    detailHeader.style.display =
        "none";


    hud.style.display =
        "none";


    timeline.style.display =
        "none";


    notificationPanel.style.display =
        "none";


    sosButton.style.display =
        "none";


    eventCard.style.display =
        "none";


    mobileAlert.style.display =
        "none";


    roomObjects.forEach(
        object => {

            object.visible =
                false;

        }
    );


    radarBody.visible =
        false;


    radarRings.forEach(
        ring => {

            ring.visible =
                false;

        }
    );


    cameraDevice.visible =
        false;


    person1.visible =
        false;

    person2.visible =
        false;

    riskHeatmap.visible =
        false;

    distanceLine.visible =
        false;

    distanceLabel.visible =
        false;


    updateOverviewUI();
}


function showDetail(
    zone
) {

    viewMode =
        "DETAIL";


    overviewPanel.style.display =
        "none";


    detailHeader.style.display =
        "block";


    hud.style.display =
        "block";


    timeline.style.display =
        "block";


    notificationPanel.style.display =
        "block";


    roomObjects.forEach(
        object => {

            object.visible =
                true;

        }
    );


    person1.visible =
        true;


    person2.visible =
        true;


    riskHeatmap.visible =
        true;


    distanceLine.visible =
        true;


    distanceLabel.visible =
        true;


    switchZone(
        zone
    );
}


// ======================================================
// 35. SWITCH ZONE
// ======================================================

function switchZone(
    zone
) {

    currentZone =
        zone;


    const config =
        zoneConfig[
            zone
        ];


    currentEventType =
        "NORMAL";


    eventCard.style.display =
        "none";


    mobileAlert.style.display =
        "none";


    document.getElementById(
        "detailZoneName"
    ).textContent =
        config.name;


    document.getElementById(
        "detailSensor"
    ).textContent =
        config.sensor;


    document.getElementById(
        "detailPrivacy"
    ).textContent =
        config.privacy;


    document.getElementById(
        "hudZoneName"
    ).textContent =
        config.name.toUpperCase();


    document.querySelectorAll(
        ".zone-button"
    ).forEach(
        button => {

            button.classList.remove(
                "active"
            );

        }
    );


    if (
        zone ===
        "TOILET"
    ) {

        document.getElementById(
            "detailToilet"
        ).classList.add(
            "active"
        );

    }


    else if (
        zone ===
        "CORRIDOR"
    ) {

        document.getElementById(
            "detailCorridor"
        ).classList.add(
            "active"
        );

    }


    else {

        document.getElementById(
            "detailStaircase"
        ).classList.add(
            "active"
        );

    }


    const radarMode =
        config.device ===
        "RADAR";


    radarBody.visible =
        radarMode;


    radarRings.forEach(
        ring => {

            ring.visible =
                radarMode;

        }
    );


    cameraDevice.visible =
        !radarMode;


    sosButton.style.display =
        zone ===
        "TOILET"
            ? "block"
            : "none";


    updateResponseUI();


    logEvent(
        "Opened " +
        config.name
    );
}


// ======================================================
// 36. NAVIGATION EVENTS
// ======================================================

document.getElementById(
    "overviewToilet"
).addEventListener(
    "click",
    () => {

        showDetail(
            "TOILET"
        );

    }
);


document.getElementById(
    "overviewCorridor"
).addEventListener(
    "click",
    () => {

        showDetail(
            "CORRIDOR"
        );

    }
);


document.getElementById(
    "overviewStaircase"
).addEventListener(
    "click",
    () => {

        showDetail(
            "STAIRCASE"
        );

    }
);


document.getElementById(
    "backOverview"
).addEventListener(
    "click",
    showOverview
);


document.getElementById(
    "detailToilet"
).addEventListener(
    "click",
    () => {

        switchZone(
            "TOILET"
        );

    }
);


document.getElementById(
    "detailCorridor"
).addEventListener(
    "click",
    () => {

        switchZone(
            "CORRIDOR"
        );

    }
);


document.getElementById(
    "detailStaircase"
).addEventListener(
    "click",
    () => {

        switchZone(
            "STAIRCASE"
        );

    }
);


document.getElementById(
    "mobileOpenIncident"
).addEventListener(
    "click",
    () => {

        mobileAlert.style.display =
            "none";

    }
);


// ======================================================
// 37. SOS BUTTON
// ======================================================

sosButton.addEventListener(
    "click",
    () => {

        if (
            currentZone !==
            "TOILET"
        ) {

            return;

        }


        sosActive =
            !sosActive;


        if (
            sosActive
        ) {

            sosButton.textContent =
                "SOS ACTIVE — RESET";


            sosButton.style.background =
                "#7f1d1d";


            logEvent(
                "SOS activated • Toilet Block B"
            );

        }


        else {

            sosButton.textContent =
                "SOS EMERGENCY";


            sosButton.style.background =
                "#dc2626";


            logEvent(
                "SOS manually reset"
            );

        }

    }
);


// ======================================================
// 38. MOVEMENT SIMULATION
// ======================================================

function updateMovement() {

    simulationTime +=
        0.01;


    const cycle =
        simulationTime %
        15;


    fallDetected =
        false;


    if (
        cycle <
        3
    ) {

        person1.position.set(
            -2,
            0,
            0.4
        );


        person2.position.set(
            2,
            0,
            0.7
        );


        person1.rotation.z =
            0;


        person2.rotation.z =
            0;

    }


    else if (
        cycle <
        6
    ) {

        const progress =
            (
                cycle -
                3
            ) /
            3;


        person1.position.set(

            -2 +
            progress *
            1.65,

            0,

            0.4

        );


        person2.position.set(

            2 -
            progress *
            1.65,

            0,

            0.55

        );


        person1.rotation.z =
            0;


        person2.rotation.z =
            0;

    }


    else if (
        cycle <
        9
    ) {

        const t =
            cycle -
            6;


        person1.position.set(

            -0.30 +
            Math.sin(
                t *
                12
            ) *
            0.12,

            0,

            0.45 +
            Math.cos(
                t *
                10
            ) *
            0.12

        );


        person2.position.set(

            0.30 +
            Math.sin(
                t *
                12 +
                Math.PI
            ) *
            0.12,

            0,

            0.55 +
            Math.cos(
                t *
                10 +
                Math.PI
            ) *
            0.12

        );


        person1.rotation.z =
            0;


        person2.rotation.z =
            0;

    }


    else if (
        cycle <
        11
    ) {

        fallDetected =
            true;


        person1.position.set(
            -0.15,
            0.25,
            0.45
        );


        person2.position.set(
            0.35,
            0,
            0.55
        );


        person1.rotation.z =
            Math.PI /
            2;


        person2.rotation.z =
            0;

    }


    else {

        const progress =
            (
                cycle -
                11
            ) /
            4;


        person1.rotation.z =
            0;


        person2.rotation.z =
            0;


        person1.position.set(

            -0.35 -
            progress *
            1.65,

            0,

            0.4

        );


        person2.position.set(

            0.35 +
            progress *
            1.65,

            0,

            0.7

        );

    }
}


// ======================================================
// 39. SENSOR CALCULATIONS
// ======================================================

function calculateDistance() {

    const dx =
        person2.position.x -
        person1.position.x;


    const dz =
        person2.position.z -
        person1.position.z;


    return Math.sqrt(
        dx * dx +
        dz * dz
    );
}


function calculateSpeed() {

    const speed1 =
        person1.position.distanceTo(
            previousPosition1
        );


    const speed2 =
        person2.position.distanceTo(
            previousPosition2
        );


    previousPosition1.copy(
        person1.position
    );


    previousPosition2.copy(
        person2.position
    );


    return (
        speed1 +
        speed2
    ) /
    2;
}


function calculateMotion(
    speed
) {

    return Math.min(
        100,
        Math.round(
            speed *
            3500
        )
    );
}


function updateCloseContact(
    distance
) {

    if (
        distance <
        1
    ) {

        if (
            closeContactStartTime ===
            null
        ) {

            closeContactStartTime =
                performance.now();

        }


        closeContactDuration =
            (
                performance.now() -
                closeContactStartTime
            ) /
            1000;

    }


    else {

        closeContactStartTime =
            null;


        closeContactDuration =
            0;

    }


    return closeContactDuration;
}


// ======================================================
// 40. INTERACTION RISK
// ======================================================

function calculateInteractionRisk(
    distance,
    motion,
    duration
) {

    let proximityRisk =
        10;


    if (
        distance <
        0.6
    ) {

        proximityRisk =
            100;

    }


    else if (
        distance <
        1
    ) {

        proximityRisk =
            80;

    }


    else if (
        distance <
        1.5
    ) {

        proximityRisk =
            55;

    }


    else if (
        distance <
        2
    ) {

        proximityRisk =
            30;

    }


    let durationRisk =
        0;


    if (
        duration >=
        5
    ) {

        durationRisk =
            100;

    }


    else if (
        duration >=
        2
    ) {

        durationRisk =
            50;

    }


    return Math.min(

        100,

        Math.round(

            proximityRisk *
            0.45

            +

            motion *
            0.40

            +

            durationRisk *
            0.15

        )

    );
}


// ======================================================
// 41. EVENT CLASSIFICATION
// ======================================================

function classifyEvent(
    interactionRisk
) {

    if (
        currentZone ===
        "TOILET" &&
        sosActive
    ) {

        return {

            type:
                "SOS",

            priority:
                "CRITICAL"

        };

    }


    if (
        fallDetected
    ) {

        return {

            type:
                "POSSIBLE_FALL",

            priority:
                "HIGH"

        };

    }


    if (
        interactionRisk >=
        75
    ) {

        return {

            type:
                "INTERACTION_ANOMALY",

            priority:
                "VERIFY"

        };

    }


    return {

        type:
            "NORMAL",

        priority:
            "MONITOR"

    };
}


// ======================================================
// 42. ZONE STATUS
// ======================================================

function updateZoneStatus(
    event
) {

    let status =
        "NORMAL";


    if (
        event.type ===
        "SOS"
    ) {

        status =
            "CRITICAL";

    }


    else if (
        event.type ===
        "POSSIBLE_FALL"
    ) {

        status =
            "HIGH";

    }


    else if (
        event.type ===
        "INTERACTION_ANOMALY"
    ) {

        status =
            "VERIFY";

    }


    zoneConfig[
        currentZone
    ].status =
        status;


    updateOverviewUI();
}


// ======================================================
// 43. PERSON COLOR
// ======================================================

function setPersonColor(
    person,
    color
) {

    person.traverse(
        child => {

            if (
                child.isMesh &&
                child.material
            ) {

                child.material.color.setHex(
                    color
                );

            }

        }
    );
}


// ======================================================
// 44. VISUAL STATE
// ======================================================

function updateVisualState(
    interactionRisk,
    event
) {

    let color =
        0x22c55e;


    let intensity =
        interactionRisk;


    if (
        event.type ===
        "SOS"
    ) {

        color =
            0xdc2626;


        intensity =
            100;


        heatmapMaterial.opacity =
            0.45;

    }


    else if (
        event.type ===
        "POSSIBLE_FALL"
    ) {

        color =
            0xef4444;


        intensity =
            90;


        heatmapMaterial.opacity =
            0.38;

    }


    else {

        if (
            interactionRisk <
            25
        ) {

            color =
                0x22c55e;

        }


        else if (
            interactionRisk <
            50
        ) {

            color =
                0xeab308;

        }


        else if (
            interactionRisk <
            75
        ) {

            color =
                0xf97316;

        }


        else {

            color =
                0xef4444;

        }


        heatmapMaterial.opacity =
            0.14 +
            interactionRisk /
            100 *
            0.22;

    }


    setPersonColor(
        person1,
        color
    );


    setPersonColor(
        person2,
        color
    );


    distanceLine.material.color.setHex(
        color
    );


    heatmapMaterial.color.setHex(
        color
    );


    radarRings.forEach(
        ring => {

            ring.material.color.setHex(
                color
            );

        }
    );


    const size =
        0.8 +
        intensity /
        100 *
        1.5;


    riskHeatmap.scale.set(
        size,
        size,
        1
    );
}


// ======================================================
// 45. BUTTON HELPER
// ======================================================

function createActionButton(
    label,
    background,
    color,
    onClick
) {

    const button =
        document.createElement(
            "button"
        );


    button.textContent =
        label;


    button.className =
        "action-button";


    button.style.background =
        background;


    button.style.color =
        color;


    button.addEventListener(
        "click",
        onClick
    );


    return button;
}


// ======================================================
// 46. EVENT CARD
// ======================================================

function updateEventCard(
    event
) {

    const title =
        document.getElementById(
            "eventTitle"
        );


    const description =
        document.getElementById(
            "eventDescription"
        );


    const priority =
        document.getElementById(
            "eventPriority"
        );


    const actions =
        document.getElementById(
            "eventActions"
        );


    actions.innerHTML =
        "";


    if (
        event.type ===
        "NORMAL"
    ) {

        eventCard.style.display =
            "none";

        return;

    }


    eventCard.style.display =
        "block";


    // ==================================================
    // SOS
    // ==================================================

    if (
        event.type ===
        "SOS"
    ) {

        eventCard.style.border =
            "2px solid #dc2626";


        eventCard.style.background =
            "#fff7f7";


        title.textContent =
            "🔴 SOS EMERGENCY";


        title.style.color =
            "#991b1b";


        description.textContent =
            "SOS activated in Toilet Block B. Immediate response required.";


        priority.textContent =
            "Priority: CRITICAL";


        priority.style.color =
            "#dc2626";


        const notify =
            createActionButton(

                "Notify + Dispatch",

                "#dc2626",

                "white",

                () => {

                    dispatchResponder(
                        event
                    );


                    description.textContent =
                        zoneConfig[
                            currentZone
                        ].responder
                        +
                        " notified and en route.";


                    actions.innerHTML =
                        "";


                    addResponseButtons(
                        actions
                    );

                }

            );


        actions.append(
            notify
        );

    }


    // ==================================================
    // FALL
    // ==================================================

    else if (
        event.type ===
        "POSSIBLE_FALL"
    ) {

        eventCard.style.border =
            "2px solid #f97316";


        eventCard.style.background =
            "#fffaf5";


        title.textContent =
            "⚠ POSSIBLE FALL";


        title.style.color =
            "#c2410c";


        description.textContent =
            "Possible fall detected in "
            +
            zoneConfig[
                currentZone
            ].name
            +
            ".";


        priority.textContent =
            "Priority: HIGH";


        priority.style.color =
            "#c2410c";


        const check =
            createActionButton(

                "Check Status",

                "#f97316",

                "white",

                () => {

                    description.textContent =
                        "Status verification requested.";


                    logEvent(
                        "Fall status verification requested"
                    );

                }

            );


        const notify =
            createActionButton(

                "Notify + Dispatch",

                "#2563eb",

                "white",

                () => {

                    dispatchResponder(
                        event
                    );


                    description.textContent =
                        zoneConfig[
                            currentZone
                        ].responder
                        +
                        " notified and en route.";


                    actions.innerHTML =
                        "";


                    addResponseButtons(
                        actions
                    );

                }

            );


        actions.append(
            check,
            notify
        );

    }


    // ==================================================
    // INTERACTION ANOMALY
    // ==================================================

    else if (
        event.type ===
        "INTERACTION_ANOMALY"
    ) {

        eventCard.style.border =
            "2px solid #eab308";


        eventCard.style.background =
            "#fffdf5";


        title.textContent =
            "⚠ INTERACTION ANOMALY";


        title.style.color =
            "#a16207";


        description.textContent =
            "Unusual proximity and rapid movement detected. Human verification required.";


        priority.textContent =
            "Priority: VERIFY FIRST";


        priority.style.color =
            "#a16207";


        const verify =
            createActionButton(

                "Verify",

                "#eab308",

                "#422006",

                () => {

                    description.textContent =
                        "Verification complete. Does this require intervention?";


                    actions.innerHTML =
                        "";


                    const escalate =
                        createActionButton(

                            "Escalate + Notify",

                            "#dc2626",

                            "white",

                            () => {

                                dispatchResponder(
                                    event
                                );


                                description.textContent =
                                    "Incident escalated. Responder notified and dispatched.";


                                actions.innerHTML =
                                    "";


                                addResponseButtons(
                                    actions
                                );

                            }

                        );


                    const noAction =
                        createActionButton(

                            "No Action Needed",

                            "#16a34a",

                            "white",

                            () => {

                                zoneConfig[
                                    currentZone
                                ].status =
                                    "NORMAL";


                                currentEventType =
                                    "NORMAL";


                                eventCard.style.display =
                                    "none";


                                logEvent(
                                    "Interaction anomaly cleared after verification"
                                );


                                updateOverviewUI();

                            }

                        );


                    actions.append(
                        escalate,
                        noAction
                    );

                }

            );


        actions.append(
            verify
        );

    }
}


// ======================================================
// 47. ARRIVED + RESOLVE BUTTONS
// ======================================================

function addResponseButtons(
    actions
) {

    const arrived =
        createActionButton(

            "Mark Arrived",

            "#2563eb",

            "white",

            () => {

                markResponderArrived();

            }

        );


    const resolve =
        createActionButton(

            "Resolve Incident",

            "#16a34a",

            "white",

            () => {

                resolveIncident();

            }

        );


    actions.append(
        arrived,
        resolve
    );
}


// ======================================================
// 48. EVENT UPDATE
// ======================================================

function updateEvent(
    event
) {

    updateZoneStatus(
        event
    );


    if (
        event.type !==
        currentEventType
    ) {

        currentEventType =
            event.type;


        if (
            event.type !==
            "NORMAL"
        ) {

            logEvent(
                event.type.replaceAll(
                    "_",
                    " "
                )
                +
                " • "
                +
                zoneConfig[
                    currentZone
                ].name
            );

        }


        if (
            viewMode ===
            "DETAIL"
        ) {

            updateEventCard(
                event
            );

        }

    }
}


// ======================================================
// 49. HUD
// ======================================================

function updateHUD(
    distance,
    motion,
    duration,
    interactionRisk,
    event
) {

    document.getElementById(
        "hudDistance"
    ).textContent =
        distance.toFixed(
            2
        )
        +
        " m";


    document.getElementById(
        "hudMotion"
    ).textContent =
        motion
        +
        "%";


    document.getElementById(
        "hudDuration"
    ).textContent =
        duration.toFixed(
            1
        )
        +
        " s";


    const fall =
        document.getElementById(
            "hudFall"
        );


    fall.textContent =
        fallDetected
            ? "DETECTED"
            : "No";


    fall.style.color =
        fallDetected
            ? "#dc2626"
            : "#0f172a";


    // ==================================================
    // AI RISK
    // ==================================================

    document.getElementById(
        "hudRisk"
    ).textContent =
        interactionRisk;


    const riskStatus =
        document.getElementById(
            "hudInteractionStatus"
        );


    if (
        interactionRisk <
        25
    ) {

        riskStatus.textContent =
            "NORMAL";


        riskStatus.style.background =
            "#dcfce7";


        riskStatus.style.color =
            "#15803d";

    }


    else if (
        interactionRisk <
        50
    ) {

        riskStatus.textContent =
            "OBSERVE";


        riskStatus.style.background =
            "#fef9c3";


        riskStatus.style.color =
            "#a16207";

    }


    else if (
        interactionRisk <
        75
    ) {

        riskStatus.textContent =
            "ELEVATED";


        riskStatus.style.background =
            "#ffedd5";


        riskStatus.style.color =
            "#c2410c";

    }


    else {

        riskStatus.textContent =
            "HIGH";


        riskStatus.style.background =
            "#fee2e2";


        riskStatus.style.color =
            "#b91c1c";

    }


    // ==================================================
    // EVENT
    // ==================================================

    const eventType =
        document.getElementById(
            "hudEventType"
        );


    const eventPriority =
        document.getElementById(
            "hudEventPriority"
        );


    if (
        event.type ===
        "SOS"
    ) {

        eventType.textContent =
            "SOS";


        eventType.style.color =
            "#dc2626";


        eventPriority.textContent =
            "CRITICAL";


        eventPriority.style.background =
            "#fee2e2";


        eventPriority.style.color =
            "#b91c1c";

    }


    else if (
        event.type ===
        "POSSIBLE_FALL"
    ) {

        eventType.textContent =
            "POSSIBLE FALL";


        eventType.style.color =
            "#f97316";


        eventPriority.textContent =
            "HIGH";


        eventPriority.style.background =
            "#ffedd5";


        eventPriority.style.color =
            "#c2410c";

    }


    else if (
        event.type ===
        "INTERACTION_ANOMALY"
    ) {

        eventType.textContent =
            "INTERACTION";


        eventType.style.color =
            "#eab308";


        eventPriority.textContent =
            "VERIFY";


        eventPriority.style.background =
            "#fef9c3";


        eventPriority.style.color =
            "#a16207";

    }


    else {

        eventType.textContent =
            "NONE";


        eventType.style.color =
            "#0f172a";


        eventPriority.textContent =
            "MONITOR";


        eventPriority.style.background =
            "#f1f5f9";


        eventPriority.style.color =
            "#64748b";

    }


    updateResponseUI();
}


// ======================================================
// 50. RADAR ANIMATION
// ======================================================

function updateRadarScan() {

    radarRings.forEach(
        (
            ring,
            index
        ) => {

            const cycle =
                (
                    simulationTime *
                    0.7
                    +
                    index *
                    0.33
                )
                %
                1;


            const scale =
                1
                +
                cycle *
                7;


            ring.scale.set(
                scale,
                scale,
                1
            );


            ring.material.opacity =
                0.55
                *
                (
                    1 -
                    cycle
                );

        }
    );
}


// ======================================================
// 51. ANIMATION LOOP
// ======================================================

function animate() {

    requestAnimationFrame(
        animate
    );


    updateMovement();


    updateRadarScan();


    updateDistanceLine();


    const distance =
        calculateDistance();


    const speed =
        calculateSpeed();


    const motion =
        calculateMotion(
            speed
        );


    const duration =
        updateCloseContact(
            distance
        );


    const interactionRisk =
        calculateInteractionRisk(
            distance,
            motion,
            duration
        );


    const event =
        classifyEvent(
            interactionRisk
        );


    updateVisualState(
        interactionRisk,
        event
    );


    updateHUD(
        distance,
        motion,
        duration,
        interactionRisk,
        event
    );


    updateEvent(
        event
    );


    const middleX =
        (
            person1.position.x
            +
            person2.position.x
        )
        /
        2;


    const middleZ =
        (
            person1.position.z
            +
            person2.position.z
        )
        /
        2;


    riskHeatmap.position.set(
        middleX,
        0.04,
        middleZ
    );


    distanceLabel.position.set(
        middleX,
        1.9,
        middleZ
    );


    updateSpriteText(

        distanceLabel,

        distance.toFixed(
            2
        )
        +
        " m"

    );


    controls.update();


    renderer.render(
        scene,
        camera
    );
}


// ======================================================
// 52. START
// ======================================================

showOverview();

animate();


// ======================================================
// 53. RESIZE
// ======================================================

window.addEventListener(
    "resize",
    () => {

        camera.aspect =
            window.innerWidth
            /
            window.innerHeight;


        camera.updateProjectionMatrix();


        renderer.setSize(
            window.innerWidth,
            window.innerHeight
        );

    }
);