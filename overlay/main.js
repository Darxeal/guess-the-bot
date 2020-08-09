let POLL_INTERVAL = 500;
let JSON_PATH = 'data.json';

let app = new Vue({
    el: '#app',
    data: {
        info: {
            "votableBots": [
                {
                    "name": "BotimusPrime",
                    "command": "0",
                    "voteStatus": [null, false]
                },
                {
                    "name": "Wildfire",
                    "command": "1",
                    "voteStatus": [true, false]
                }
            ],
            "mysteryBots": [
                {
                    "identifier": "A",
                    "team": "blue",
                    "actualName": null,
                    "guessed": false,
                    "guessedBy": null
                },
                {
                    "identifier": "B",
                    "team": "orange",
                    "actualName": "Wildfire",
                    "guessed": true,
                    "guessedBy": "Robbie"
                }
            ]
        }
    },
    methods: {
        async loadData() {
            try {
                const res = await $.get("data.json");
                this.info = JSON.parse(res);
            } catch (err) {
                document.getElementById("app").innerHTML = err.message;
            }
        }
    },
    created: function() {
        this.loadData();
        setInterval(this.loadData, POLL_INTERVAL);
    }
});