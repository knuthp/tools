import htmlPlugin from "eslint-plugin-html";
import js from "@eslint/js";
import globals from "globals";

export default [
    js.configs.recommended,
    {
        files: ["**/*.html"],
        plugins: {
            html: htmlPlugin
        },
        languageOptions: {
            ecmaVersion: "latest",
            sourceType: "module",
            globals: {
                ...globals.browser,
                ...globals.node,
                deck: "readonly",
                maplibregl: "readonly",
                d3: "readonly",
                // p5.js globals
                setup: "readonly",
                draw: "readonly",
                createCanvas: "readonly",
                background: "readonly",
                fill: "readonly",
                noStroke: "readonly",
                rect: "readonly",
                ellipse: "readonly",
                triangle: "readonly",
                text: "readonly",
                textAlign: "readonly",
                textSize: "readonly",
                width: "readonly",
                height: "readonly",
                windowWidth: "readonly",
                windowHeight: "readonly",
                resizeCanvas: "readonly",
                image: "readonly",
                createImage: "readonly",
                color: "readonly",
                millis: "readonly",
                dist: "readonly",
                distSq: "readonly",
                lerp: "readonly",
                constrain: "readonly",
                random: "readonly",
                floor: "readonly",
                ceil: "readonly",
                round: "readonly",
                abs: "readonly",
                min: "readonly",
                max: "readonly",
                sin: "readonly",
                cos: "readonly",
                tan: "readonly",
                sqrt: "readonly",
                pow: "readonly",
                exp: "readonly",
                log: "readonly",
                map: "readonly",
                norm: "readonly",
                noise: "readonly",
                push: "readonly",
                pop: "readonly",
                translate: "readonly",
                rotate: "readonly",
                scale: "readonly",
                imageMode: "readonly",
                rectMode: "readonly",
                key: "readonly",
                keyCode: "readonly",
                keyIsDown: "readonly",
                mouseIsPressed: "readonly",
                mouseX: "readonly",
                mouseY: "readonly",
                pmouseX: "readonly",
                pmouseY: "readonly",
                touches: "readonly",
                getAudioContext: "readonly",
                frameCount: "readonly",
                noSmooth: "readonly",
                p5: "readonly",
                LEFT_ARROW: "readonly",
                RIGHT_ARROW: "readonly",
                UP_ARROW: "readonly",
                DOWN_ARROW: "readonly",
                CENTER: "readonly",
                LEFT: "readonly",
                RIGHT: "readonly",
                TOP: "readonly",
                BOTTOM: "readonly"
            }
        },
        rules: {
            "no-unused-vars": "warn",
            "no-console": "off",
            "no-undef": "error"
        }
    },
    {
        files: ["**/*.js"],
        languageOptions: {
            ecmaVersion: "latest",
            sourceType: "module",
            globals: {
                ...globals.browser,
                ...globals.node,
                deck: "readonly",
                maplibregl: "readonly"
            }
        },
        rules: {
            "no-unused-vars": "warn",
            "no-console": "off"
        }
    }
];
