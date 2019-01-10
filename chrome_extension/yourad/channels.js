// Must run on background page

// TODO: make google search results ALWAYS show photos.  Special case it.

var gCadences = {'daily': 1000*60*60*24,
                'bi-weekly': 1000*60*60*24*3.5,
                'weekly': 1000*60*60*24*7,
                'bi-monthly': 1000*60*60*24*14,
                'monthly': 1000*60*60*24*30,
                'quarterly': 1000*60*60*24*90,
                'bi-annually': 1000*60*60*24*182};

// Inputs: width:int, height:int, url:url, title:string, attribution_url:url
class Listing {
    constructor(data) {
        this.width = data.width;
        this.height = data.height;
        this.url = data.url;
        this.click_url = data.click_url;
        this.ad_name = data.ad_name;
        this.ad_campaign = data.ad_campaign;
        this.ad_success = data.ad_success;
    }
}


class ChannelYourAd {

    constructor() {
        var that = this;
        this.__ads = [];
        this.__listings = [];
        this._loadFromStorage();
    }


    _getClosestListings(targ_val, func){
        //return an array of listings whose val, when you apply 'func' to the listing,
        //is closest to targ_val.  i.e. pass it a width target and a
        //function(l) { return l.width; } to get an array with listings with
        //closest width to target width.

        var best = [];
        var best_val = 999;
        for (var i in this.__listings){
            var l_val = func(this.__listings[i]);
            var diff = Math.abs(targ_val - l_val);
            if (diff <= best_val){
                if (diff == best_val){
                    best.push(this.__listings[i]);
                } else {
                    best = [this.__listings[i]];
                    best_val = diff;
                }
            }
        }

        return best;
    }

    randomListing(opts) {
        //main return listing for ad replacement.  Can get
        //width/height/either/none, will otherwise be undefined.

        if (opts.width && opts.height) {
            var temp_listings = this._getClosestListings(opts.width/opts.height, function(l) { return l.width/l.height; });
            var randomIndex = Math.floor(Math.random() * temp_listings.length);
            return temp_listings[randomIndex];

        } else if (opts.width) {
            var temp_listings = this._getClosestListings(opts.width, function(l) { return l.width; });
            var randomIndex = Math.floor(Math.random() * temp_listings.length);
            return temp_listings[randomIndex];

        } else if (opts.height) {
            var temp_listings = this._getClosestListings(opts.height, function(l) { return l.height; });
            var randomIndex = Math.floor(Math.random() * temp_listings.length);
            return temp_listings[randomIndex];

        } else {
            var randomIndex = Math.floor(Math.random() * this.__listings.length);
            return this.__listings[randomIndex];
        }

    }

    _loadFromStorage() {

        var that = this;
        var ads = storage_get("ads");

        if (!ads || ~ads.length || (ads.length > 0 && !ads[0].name)) {
            // Default, load from json_ad
            var temp = chrome.runtime.getURL("yourad/generated/ad_data.json");
            var jresp = $.getJSON(temp, function(result){

                var files_to_use = [];
                var jblob = jresp['responseJSON'];

                var ads_temp = {};

                for (var i in jblob['ads']){
                    ads_temp[jblob['ads'][i].name] = {
                        cadence: gCadences[jblob['ads'][i].cadence], //transform to ms
                        campaign: jblob['ads'][i].campaign,
                        files: jblob['ads'][i].files,
                        image: jblob['ads'][i].image,
                        last_accomplished: jblob['ads'][i].last_accomplished,
                        should_show: jblob['ads'][i].should_show,
                        success: jblob['ads'][i].success,
                        text: jblob['ads'][i].text
                    };
                }

                that.__ads = ads_temp;
                that._cacheListings();
            });
        } else {

            this.__ads = ads;
            this._cacheListings();

        }

    }

    _saveToStorage() {
        storage_set("ads", this.__ads);
    }


    clickAd(details){
        this.__ads[details.name].last_accomplished = Date.now(); //update ad
        this._cacheListings(); //update cache
    }


    _cacheListings(){

        function ListingAd(ad_name, ad, file_desc) {
            var folder = chrome.runtime.getURL("yourad/");
            var options_url = chrome.extension.getURL("options/index.html");

            return new Listing({
                width: file_desc[0][0],
                height: file_desc[0][1],
                url: folder + file_desc[1],
                ad_name: ad_name,
                ad_campaign: ad.campaign,
                ad_success: ad.success,
                click_url: options_url
            });
        }

        //run through ads, look at cadence/last_shown, update should_show.
        for (var n in this.__ads){
            console.log(this.__ads[n]);
            if (this.__ads[n].last_accomplished){
                if (Date.now() - this.__ads[n].last_accomplished  < this.__ads[n].cadence) {
                    this.__ads[n].should_show = false;
                } else {
                    this.__ads[n].should_show = true;
                }
            } else {
                this.__ads[n].should_show = true;
            }
        }

        //save it
        this._saveToStorage();

        //update __listing list with all that we should_show
        var listings = [];

        for (var ad_name in this.__ads) {

            if (this.__ads[ad_name].should_show) {
                for (var f in this.__ads[ad_name]['files']) {

                    var fl = this.__ads[ad_name]['files'][f];
                    var pushme = ListingAd(ad_name, this.__ads[ad_name], fl);
                    listings.push(pushme);
                }
            }
        }

        this.__listings = listings;

    }

}

//Legacy, working code:

/*

// Contains and provides access to all the photo channels.
class Channels {
    constructor() {
        var that = this;
        this._channelGuide = undefined; // maps channel ids to channels and metadata
        this._loadFromStorage();
        this.refreshAllEnabled();
        window.setInterval(
            function() { that.refreshAllEnabled(); },
            1000 * 60 * 60 * 24
        );
    }

    // Inputs:
    //   name:string - a Channel class name.
    //   param:object - the single ctor parameter to the Channel class.
    //   enabled:bool - true if this channel is to be used for pictures.
    // Returns:
    //   id of newly created channel, or undefined if the channel already existed.
    add(data) {
        // Check, whether such a class exists
        var klass = null;
        switch (data.name) {
            case "LocalChannel": klass = LocalChannel;
                break;
            default: return;
        }
        var dataParam = JSON.stringify(data.param);
        for (var id in this._channelGuide) {
            var c = this._channelGuide[id];
            if (c.name === data.name && JSON.stringify(c.param) === dataParam) {
                return;
            }
        }
        var id = Math.floor(Math.random() * Date.now());
        var channel = new klass(data.param);
        this._channelGuide[id] = {
            name: data.name,
            param: data.param,
            enabled: data.enabled,
            channel: channel
        };
        this._saveToStorage();
        var that = this;
        $(channel).on("updated", function() {
            // TODO: make sure this works in Safari.  And if you fix a bug, fix it
            // in AdBlock too -- it's keeping filter update events from showing up
            // in the AdBlock Options page I think.
            chrome.runtime.sendMessage({ command: "channel-updated", id: id });
            if (that._channelGuide[id].enabled) {
                that._channelGuide[id].channel.prefetch();
            }
        });
        channel.refresh();
        return id;
    }

    remove(channelId) {
        delete this._channelGuide[channelId];
        this._saveToStorage();
    }

    // Return read-only map from each channel ID to
    // { name, param, enabled }.
    getGuide() {
        var results = {};
        for (var id in this._channelGuide) {
            var c = this._channelGuide[id];
            results[id] = {
                name: c.name,
                param: c.param,
                enabled: c.enabled
            };
        }

        return results;
    }

    getListings(id) {
        return this._channelGuide[id].channel.getListings();
    }

    setEnabled(id, enabled) {
        this._channelGuide[id].enabled = enabled;
        this._saveToStorage();
    }

    refreshAllEnabled() {
        for (var id in this._channelGuide) {
            var data = this._channelGuide[id];
            if (data.enabled) {
                data.channel.refresh();
            }
        }
    }

    // Returns a random Listing from all enabled channels or from channel
    // |channelId| if specified, trying to match the ratio of |width| and
    // |height| decently.  Returns undefined if there are no enabled channels.
    randomListing(opts) {
        var allListings = [];

        for (var id in this._channelGuide) {
            var data = this._channelGuide[id];
            if (opts.channelId === id || (data.enabled && !opts.channelId)) {
                allListings.push.apply(allListings, data.channel.getListings());
            }
        }
        // TODO: care about |width| and |height|
        var randomIndex = Math.floor(Math.random() * allListings.length);
        return allListings[randomIndex];
    }

    clickAd(details){
    //manage ad state
    console.log("CLICK MADE IT");
    console.log(details);
    }

    _loadFromStorage() {
        this._channelGuide = {};

        var entries = storage_get("channels");
        if (!entries || (entries.length > 0 && !entries[0].name)) {
            // Default set of channels
            if (storage_get("project_cats")) {
                this.add({ name: "LocalChannel", param: undefined, enabled: true });
            } else {
                this.add({ name: "LocalChannel", param: undefined, enabled: true });
            }
        } else {
            for (var i=0; i < entries.length; i++) {
                this.add(entries[i]);
            }
        }
    }

    _saveToStorage() {
        var toStore = [];
        var guide = this.getGuide();
        for (var id in guide) {
            toStore.push(guide[id]);
        }
        storage_set("channels", toStore);
    }
}

// Base class representing a channel of photos.
// Concrete constructors must accept a single argument, because Channels.add()
// relies on that.
class Channel {
    constructor() {
        this.__listings = [];
    }

    getListings() {
        return this.__listings.slice(0); // shallow copy
    }

    // Update the channel's listings and trigger an 'updated' event.
    refresh() {
        var that = this;
        this._getLatestListings(function(listings) {
            that.__listings = listings;
            $(that).trigger("updated");
        });
    }

    // Load all photos so that they're in the cache.
    prefetch() {
        this.__listings.forEach(function(listing) {
            setTimeout(function() {
                new Image().src = listing.url;
            }, 0);
        });
    }

    _getLatestListings() {
        throw new Error("Implemented by subclass. Call callback with up-to-date listings.");
    }
}

// Channel containing hard coded cats loaded from disk.
class LocalChannel extends Channel {
    constructor() {
        super();
    }


    _getLatestListings(callback) {

        function ListingAd(ad, file_desc) {
            var folder = chrome.runtime.getURL("yourad/");
            var options_url = chrome.extension.getURL("options/index.html");

            return new Listing({
                width: file_desc[0][0],
                height: file_desc[0][1],
                url: folder + file_desc[1],
                ad_name: ad.name,
                ad_campaign: ad.campaign,
                ad_success: ad.success,
                click_url: options_url
            });
        }

        // load the list dynamically from what's in the folder
        var temp = chrome.runtime.getURL("yourad/generated/ad_data.json");
        var jresp = $.getJSON(temp, function(result){

            var files_to_use = [];
            var jblob = jresp['responseJSON'];
            console.log(jblob['ads']);

            for (var ad in jblob['ads']) {
                for (var f in jblob['ads'][ad]['files']) {

                    var fl = jblob['ads'][ad]['files'][f];
                    var pushme = ListingAd(jblob['ads'][ad], fl);

                    files_to_use.push(pushme);
                }
            }

            callback(files_to_use);

        });


        //callback([
        //    L(180, 150, "dad_180x150.png"),
        //    L(728, 90,  "dad_728x90.png"),
        //    L(300, 250, "dad_300x250.png"),
        //    L(160, 600, "dad_160x600.png")
        //]);

    }

}
*/
