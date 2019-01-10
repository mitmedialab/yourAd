
/// ADD ACCOMPLISHMENT LISTENER
chrome.runtime.onMessage.addListener(
    function(request){
        if (request.command !== 'accomplishment-update') { return; }
        console.log("UPDATE DETECTED");
        load_accomplishments_page();
    }
);

function load_accomplishments_page(){
    //call background page storage and get all accomplishments
    BGcall("getAccomplishments", function(accomplishments){

        //on cb, clear the main accomplishments div
        $("#accomplishments").empty();

        //add each accomplishment with timestamp, formatted
        for (var a=accomplishments.length-1; a>=0; a--){

            var a_item = $("<div>", {"class": "a-item"});
            var date_item = $("<p>", {"class": "a-date"});
            var s_item = $("<p>", {"class": "s-item"});

            var c = accomplishments[a]['campaign']['bcolor'];
            a_item.css({backgroundColor:"rgb("+c[0]+","+c[1]+","+c[2]+")"});

            var curdate = new Date(accomplishments[a].timestamp);
            date_item.text(curdate.toLocaleString());

            a_item.text(accomplishments[a].success);
            s_item.text(accomplishments[a].campaign.slogan);
            a_item.prepend(date_item);
            a_item.append(s_item);

            $("#accomplishments").append(a_item);
        }
    });



}

load_accomplishments_page();
