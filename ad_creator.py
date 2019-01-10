import os, sys, random, glob, math, json, SocketServer, SimpleHTTPServer, BaseHTTPServer
import numpy as np
from PIL import Image, ImageFont, ImageDraw, ImageFilter
from colorthief import ColorThief
from seaborn import color_palette as colors
from pyfiglet import Figlet
from PyInquirer import prompt


#TODO: new add associated with old ad id (multiple ad formats/files associated with one ad name/goal/intent, so they are controlled
#      within the extension as one (if you succeed in that behavior, all relevant ads cease), instead of just that one specific ads.

#TODO: something that looks like a button to click on, text ads with button.

#TODO: logo variability-- change slogan justify on bottom of ads and save as different ads


default_sizes = {'ldrboard': (728, 90), 'med_rect': (300, 250), 'rect': (180, 150), 'wide_skyscpr': (160, 600)}

full_sizes = {
    'square': (250, 250),
    'sm_square': (200, 200),
    'banner': (468, 60),
    'leaderboard': (728, 90),
    'inline_rect': (300, 250),
    'lg_rect': (336, 280),
    'skyscraper': (120, 600),
    'wd_skyscraper': (160, 600),
    'half_page': (300, 600),
    'lg_leaderboard': (970, 90)
}


output_folder = 'chrome_extension/yourad/generated'
relative_output_folder = 'generated' # relative to yourad folder in chrome ext
input_folder = 'source'
pairing_subfolder = 'pairing'


def write_text_to_img(img, pos, text, font, font_size, color):
    # write text onto an img at position pos with font/fontsize/fontcolor
    text = text.decode('utf8')
    ft = ImageFont.truetype(font, font_size)

    draw = ImageDraw.Draw(img)
    draw.text(pos, text, font=ft, fill=color)
    del draw

    return True


def use_white_text(RGB):
    # return true if passed RGB background is dark, false if light.
    # Based on W3C percieved brightness.  Assumes 0-255 int for RGB.
    r,g,b = RGB
    return (r * 299 + g * 587 + b * 114) / 1000.0 < 123


def select_contrast_text_color(RGBBackColor):
    # return contrasting text color for passed RGB backgorund
    text_color=(70,70,70)
    if use_white_text(RGBBackColor): text_color=(245,244,237)
    return text_color


def select_random_bkcolor():
    #return random color
    bk_color = random.choice(colors('Paired'))
    return tuple(int(c*255) for c in bk_color)


def print_fonts_available(folder='fonts'):
    # print out fonts available in font folder
    print folder + ' files:'
    files = [f for f in glob.glob(os.path.join(folder, '*')) if not os.path.isdir(f)]
    for f in files: print '\t' + f[len(folder):]


def select_random_font(folder='fonts'):
    #return a path to a random font in the fonts folder
    return random.choice([f for f in glob.glob(os.path.join(folder, '*')) if not os.path.isdir(f)])


def get_text_size(font_filename, font_size, text):
    # return text size with a given font and fontsize
    font = ImageFont.truetype(font_filename, font_size)
    return font.getsize(text)


def get_smart_bkcolor(image_filename):
    # return RBG tuple of dominant color in file
    ct = ColorThief(image_filename)
    return ct.get_color(quality=1)


def get_palette(image_filename, color_count=6):
    # return a list of color palette based on image
    ct = ColorThief(image_filename)
    return ct.get_palette(color_count=color_count)


def get_smart_colors(image_filename, color_count=10):
    # return the darkest and lightest colors from the palette of an image
    # to use for text/bkground color or vice versa while matching image.
    ct = ColorThief(image_filename)
    palette = ct.get_palette(color_count=color_count)

    darkest_color, brightest_color = (), ()
    darkest_hue, brightest_hue = 255.0, 0.0

    for color in palette:
        r,g,b = color
        color_hue = (r * 299 + g * 587 + b * 114) / 1000.0

        if color_hue < darkest_hue:
            darkest_hue = color_hue
            darkest_color = color

        if color_hue > brightest_hue:
            brightest_hue = color_hue
            brightest_color = color

    return darkest_color, brightest_color


def find_nearest(array, value):
    # find the nearest value in an array
    array = np.asarray(array)
    idx = (np.abs(array - value)).argmin()
    return array[idx]


def get_json_blob(default='ad_data.json'):
    try:
        with open(os.path.join(output_folder, default)) as json_file:
            data = json.load(json_file)
        return data
    except:
        #if file doesn't exist, create new one and return
        return {'campaigns':
                    [
                    {'slogan': 'HEALTH MATTERS', 'sfont': 'fonts/Fine College.ttf', 'bcolor': (138, 38, 168)},
                    {'slogan': 'Small Choices, Big Changes.', 'sfont': 'fonts/Pacifico.ttf', 'bcolor': (38,73,168)},
                    {'slogan': 'Family First', 'sfont': 'fonts/VintageOne.ttf', 'bcolor': (38, 168, 105)},
                    {'slogan': 'be your best self', 'sfont': 'fonts/BEBAS.ttf', 'bcolor': (138, 55, 38)}
                    ],
                'ads':[]
        }


def save_json_blob(json_blob, default='ad_data.json'):
    with open(os.path.join(output_folder, default), 'w') as json_file:
        json.dump(json_blob, json_file)


def get_text_split(text, max_lines=4):
    # return array of arrays of splits given a number of lines you can split.
    # i.e. pass 'this is a test split advert' and get back [['this is a test
    # split advert'],['this is a','test split advert'], ['this is', 'a test',
    # 'split advert'], ['this is', 'a test', 'split', 'advert']]

    #one line, no split
    return_results = [[text]]

    #now step through other split options:
    for max_line in range(2, max_lines+1):

        #split on spaces
        ind_of_spaces = [n for n in xrange(len(text)) if text.find(' ', n) == n]

        #ideal inds
        ideal_inds = [i*len(text)/max_line for i in range(1,max_line)]

        #get closest ind_of_spaces for each ideal_inds
        ideal_inds = [find_nearest(ind_of_spaces, i) for i in ideal_inds]

        #split on closest indices of spaces
        words_split = [text[:ideal_inds[0]]]
        for i in range(len(ideal_inds)-1):
            words_split.append(text[ideal_inds[i]+1:ideal_inds[i+1]])
        words_split.append(text[ideal_inds[-1]+1:])

        #if any words_split are '', remove them
        words_split = [w for w in words_split if w != '']

        #now minimize lines based on longest line...
        longest = max([len(w) for w in words_split])
        combo_len = [len(words_split[i]) + len(words_split[i+1]) for i in range(len(words_split)-1)]

        #if any combo of lines is shorter than the longest line, combine them
        while(any([cl < longest for cl in combo_len])):
            min_ind = combo_len.index(min(combo_len))
            words_split[min_ind] = words_split[min_ind] + ' ' + words_split[min_ind+1]
            del words_split[min_ind+1]
            combo_len = [len(words_split[i]) + len(words_split[i+1]) for i in range(len(words_split)-1)]

        #now we have optimally split lines.  Append if a new result
        if words_split not in return_results: return_results.append(words_split)

    return return_results


def optimal_text_splits(text, font, width, height, same_size=False, max_lines=4):
    #given a size x_width, y_width, split text into lines and fill the box
    #with line wrapping optimally (largest fonts with breaks at each line)
    #handles forcing all lines to have same font size, or all lines can
    #have different font sizes if they are different lengths (same_size).
    #return [('textline1', (x_start, y_start), fontsize), ...]
    optimal_splits = get_text_split(text, max_lines)

    best_split, best_font_sizes = [], [0]
    for split in optimal_splits:

        cont = True
        font_sizes = [0]*len(split)
        add_to_font_sizes = [1]*len(split)

        while(cont):

            font_sizes = np.add(font_sizes, add_to_font_sizes)
            text_sizes = [get_text_size(font, font_sizes[i], split[i]) for i in range(len(split))]

            #check if we've maxed out our height
            full_height = np.sum(text_sizes, axis=0)[1]

            if full_height > height:
                cont = False
                font_sizes = np.subtract(font_sizes, add_to_font_sizes)

            #check if any line has maxed out its width
            for i in range(len(split)):
                if text_sizes[i][0] > width:
                    font_sizes[i] -= 1
                    add_to_font_sizes[i] = 0
                    if all([n==0 for n in add_to_font_sizes]): cont = False


        if min(font_sizes) > min(best_font_sizes):
            best_split = split
            best_font_sizes = font_sizes

        #found best split with best font_sizes

    #use smallest font size if all should be equal
    if same_size: best_font_sizes = [min(best_font_sizes)]*len(best_font_sizes)

    #find optimal x,ys
    text_sizes = [get_text_size(font, best_font_sizes[i], best_split[i]) for i in range(len(best_split))]
    start_x = [(1.0*width - s[0])/2 for s in text_sizes]

    full_height = np.sum(text_sizes, axis=0)[1]
    offset_height = (1.0*height-full_height) / 2
    cumsum_height = [0]
    cumsum_height.extend(np.cumsum(text_sizes, axis=0)[:,1])
    start_y = [offset_height + cumsum_height[i] for i in range(len(best_split))]

    return [(best_split[i], (start_x[i], start_y[i]), best_font_sizes[i]) for i in range(len(best_split))]


def feather_map(size_tuple, percent=0.3):
    #return a map of size_tuple with alpha for shading the corners
    min_dim = min(size_tuple)
    buff = min_dim*percent

    x,y = size_tuple

    mask_array=np.ones(size_tuple)*255

    for cur_x in range(size_tuple[0]):
        for cur_y in range(size_tuple[1]):

            alpha = 255

            if cur_x<buff:
                alpha = alpha - (255 - 255*((cur_x)/buff))
            if cur_x>x-buff:
                alpha = alpha - (255 - 255*((x-cur_x)/buff))
            if cur_y<buff:
                alpha = alpha - (255 - 255*((cur_y)/buff))
            if cur_y>y-buff:
                alpha = alpha - (255 - 255*((y-cur_y)/buff))

            if alpha<0:alpha=0

            mask_array[cur_x][cur_y] = alpha

    return Image.fromarray(mask_array.T.astype(np.uint8), mode='L')


def resize_and_crop(image, new_x, new_y, crop=True, feather=True, feather_percent=0.2):
    #resizes image to newx, newy, will crop to center if crop is true, otherwise picks
    #dominant color and keeps full image with dominant color background.  Can feather
    #into the background if crop is off.
    img = Image.open(image)
    x,y = img.size
    scale = (float(x) / new_x, float(y) / new_y)

    if crop:
        #crop, centered
        if scale[0] > scale[1]:
            img = img.resize((int(math.ceil(x/scale[1])), int(math.ceil(y/scale[1]))), Image.ANTIALIAS)
            img = img.crop(((x/scale[1]/2)-(new_x/2), 0, (x/scale[1]/2)+(new_x/2), new_y))
        else:
            img = img.resize((int(math.ceil(x/scale[0])), int(math.ceil(y/scale[0]))), Image.ANTIALIAS)
            img = img.crop((0, (y/scale[0]/2)-(new_y/2), new_x, (y/scale[0]/2)+(new_y/2)))

        return img

    else:
        #no crop
        bk_color = get_smart_bkcolor(image)
        img2 = Image.new('RGBA', (new_x, new_y), color=bk_color)

        if scale[0] > scale[1]:
            img = img.resize((int(math.ceil(x/scale[0])), int(math.ceil(y/scale[0]))), Image.ANTIALIAS)
            off = (0, (new_y - int(math.ceil(y/scale[0]))) // 2)
        else:
            img = img.resize((int(math.ceil(x/scale[1])), int(math.ceil(y/scale[1]))), Image.ANTIALIAS)
            off = ((new_x - int(math.ceil(x/scale[1]))) // 2, 0)

        if feather:
           feather_mask = feather_map(img.size, feather_percent)
           img2.paste(img, off, mask=feather_mask)
        else:
            img2.paste(img, off)

        return img2


def image_ad(image, ad_size, insert_pos, insert_size, fname, crop=False, feather_percent=0.1, smartbk=True):
    #try to place image in frame with blur
    #smartbk tries to use a color from the image
    #will put at pos centered at (x,y), with size.  Crop from center
    image = os.path.join(input_folder, image)

    if smartbk: bk_color = get_smart_bkcolor(image)
    else: bk_color = select_random_bkcolor()

    insert = Image.open(image)
    insert = resize_and_crop(image, insert_size[0], insert_size[1], crop=crop, feather_percent=feather_percent)

    img = Image.new('RGBA', ad_size, color=bk_color)
    img.paste(insert, insert_pos, mask=feather_map(insert.size, percent=feather_percent))
    img.save(os.path.join(output_folder, fname + '_' + str(ad_size[0]) + 'x' + str(ad_size[1]) + '.png'))


def text_ad(text, fname, font=None, bk_color=None, vary_font=True, vary_color=True, same_size_font=False, max_lines=4, padding=3):

    #initialize non-initialized bkground color and text color for contast
    if bk_color is None: bk_color = select_random_bkcolor()
    if font is None: font = select_random_font()
    text_color = select_contrast_text_color(bk_color)

    #step through ad sizes to generate
    for adsize, dims in full_sizes.iteritems():

        #if vary color flag set, for each size recompute colors
        if vary_color:
            bk_color = select_random_bkcolor()
            text_color = select_contrast_text_color(bk_color)

        if vary_font: font = select_random_font()

        img = Image.new('RGBA', dims, color=bk_color) #may need to include alpha in bk_color (bkcolor, 0)

        best_locations = optimal_text_splits(text, font, dims[0]-(2*padding), dims[1]-(2*padding), same_size=same_size_font, max_lines=max_lines)
        for (txt, xy, ftsz) in best_locations:
            write_text_to_img(img, (padding+xy[0], padding+xy[1]), txt, font, font_size=ftsz, color=text_color)

        img.save(os.path.join(output_folder, fname + '_' + str(dims[0]) + 'x' + str(dims[1]) + '.png'))


def ad_generator(ad_size, fname, text=None, tfont=None, slogan=None, sfont=None, image=None):
    #if an image, generate smartbackground, add text with font and slogan with slogan font
    #in appropriate places
    assert(text is not None or image is not None), 'must pass text or image or both'

    if tfont is None: tfont = select_random_font()
    if sfont is None: sfont = select_random_font()

    #text only ad, simple.  Slogan in bottom 1/5, text in top 4/5, with padding
    if image is None:
        bk_color = select_random_bkcolor()
        text_color = select_contrast_text_color(bk_color)

        img = Image.new('RGBA', ad_size, color=bk_color)

        t_height = 4 *ad_size[1] // 5
        s_height = ad_size[1] // 5
        padding = 3 * min(s_height, ad_size[0]) // 100

        best_locations = optimal_text_splits(text, tfont, ad_size[0]-(2*padding), t_height-(2*padding))
        for (txt, xy, ftsz) in best_locations:
            write_text_to_img(img, (padding+xy[0], padding+xy[1]), txt, tfont, font_size=ftsz, color=text_color)

        extra_pad=5
        best_locations = optimal_text_splits(slogan, sfont, ad_size[0]-(2*(padding+extra_pad)), s_height-(2*(padding+extra_pad)))
        for (txt, xy, ftsz) in best_locations:
            write_text_to_img(img, (extra_pad+padding+xy[0], t_height+extra_pad+padding+xy[1]), txt, sfont, font_size=ftsz, color=text_color)

        img.save(os.path.join(output_folder, fname + '_' + str(ad_size[0]) + 'x' + str(ad_size[1]) + '.png'))

    #image-based ad.  More complex in terms of placement, use smart background
    else:
        if ad_size[0] < 3*ad_size[1]:
            image = os.path.join(input_folder, image)
            bk_color, text_color = get_smart_colors(image)

            t_height = 2 * ad_size[1] // 8
            i_height = 5 * ad_size[1] // 8
            s_height = ad_size[1] // 8
            padding = 3 * min(s_height, ad_size[0]) // 100

            img = Image.new('RGBA', ad_size, color=bk_color)
            insert = Image.open(image)

            if text is not None:
                #text
                best_locations = optimal_text_splits(text, tfont, ad_size[0]-(2*padding), t_height-(2*padding))
                for (txt, xy, ftsz) in best_locations:
                    write_text_to_img(img, (padding+xy[0], padding+xy[1]), txt, tfont, font_size=ftsz, color=text_color)

                #image
                insert = resize_and_crop(image, ad_size[0], i_height, crop=True, feather_percent=0.15)
                img.paste(insert, (0, t_height), mask=feather_map(insert.size, percent=0.15))

            else:
                #image if no text around
                insert = resize_and_crop(image, ad_size[0], ad_size[1], crop=True, feather_percent=0.0)#i_height+t_height, crop=True, feather_percent=0.15)
                img.paste(insert, (0, 0), mask=feather_map(insert.size, percent=0.0))

            #slogan
            extra_pad=5
            best_locations = optimal_text_splits(slogan, sfont, ad_size[0]-(2*(padding+extra_pad)), s_height-(padding))
            for (txt, xy, ftsz) in best_locations:
                write_text_to_img(img, (extra_pad+padding+xy[0], t_height+i_height+(padding//2)+xy[1]), txt, sfont, font_size=ftsz, color=text_color)

            img.save(os.path.join(output_folder, fname + '_' + str(ad_size[0]) + 'x' + str(ad_size[1]) + '.png'))

        else:
            #special case for very long skinny headers/leaders
            image = os.path.join(input_folder, image)
            bk_color, text_color = get_smart_colors(image)

            padding = 3 * ad_size[1] // 100

            img = Image.new('RGBA', ad_size, color=bk_color)
            insert = Image.open(image)

            if text is None:
                #fill image and put slogan at bottom
                insert = resize_and_crop(image, ad_size[0], ad_size[1], crop=True, feather_percent=0.0)
                img.paste(insert, (0, 0))

                t_height = 4 *ad_size[1] // 5
                s_height = ad_size[1] // 5

                extra_pad=5
                best_locations = optimal_text_splits(slogan, sfont, ad_size[0]-(2*(padding+extra_pad)), s_height-(2*(padding+extra_pad)))
                for (txt, xy, ftsz) in best_locations:
                    write_text_to_img(img, (extra_pad+padding+xy[0], t_height+extra_pad+padding+xy[1]), txt, sfont, font_size=ftsz, color=text_color)

            else:
                #split screen into fifths, 2/5 for image, 3/5 for text
                i_width = 2 * ad_size[0] // 5
                t_width = 3 * ad_size[0] // 5

                insert = resize_and_crop(image, i_width, ad_size[1], crop=True, feather_percent=0.0)
                img.paste(insert, (0, 0))

                best_locations = optimal_text_splits(text, tfont, t_width-(2*padding), (3 * ad_size[1] // 4)-(2*padding))
                for (txt, xy, ftsz) in best_locations:
                    write_text_to_img(img, (i_width + padding + xy[0], padding+xy[1]), txt, tfont, font_size=ftsz, color=text_color)

                extra_pad=5
                best_locations = optimal_text_splits(slogan, sfont, t_width-(2*(padding+extra_pad)), (ad_size[1] //4)-(padding))
                for (txt, xy, ftsz) in best_locations:
                    write_text_to_img(img, (i_width + extra_pad+padding+xy[0], (3 * ad_size[1] // 4)+(padding//2)+xy[1]), txt, sfont, font_size=ftsz, color=text_color)



            img.save(os.path.join(output_folder, fname + '_' + str(ad_size[0]) + 'x' + str(ad_size[1]) + '.png'))

    #return filename of ad created
    return os.path.join(relative_output_folder, fname + '_' + str(ad_size[0]) + 'x' + str(ad_size[1]) + '.png')


def ad_wrapper(fname, text=None, tfont=None, slogan=None, sfont=None, image=None):
    assert(text is not None or image is not None), 'must pass text or image or both'

    ad_files = []

    for adsize, dims in full_sizes.iteritems():
        generated_file = ad_generator(dims,fname,text,tfont,slogan,sfont,image)
        ad_files.append([dims, generated_file])

    return ad_files


def pairing_ad_generator(ad_size, fname, img1, img2, text, slogan, sfont):
    tfont= select_random_font()

    img1 = os.path.join(input_folder, img1)
    img2 = os.path.join(input_folder, img2)
    bk_color, text_color = get_smart_colors(img2)

    img = Image.new('RGBA', ad_size, color=bk_color)
    insert1 = Image.open(img1)
    insert2 = Image.open(img2)

    if ad_size[0] < 3*ad_size[1] and ad_size[1] < 3*ad_size[0]:

        t_height = 2 * ad_size[1] // 8
        i_height = 5 * ad_size[1] // 8
        s_height = ad_size[1] // 8
        padding = 3 * min(s_height, ad_size[0]) // 100

        if text is not None:
            #print 'normal w text'
            #text
            best_locations = optimal_text_splits(text, tfont, ad_size[0]-(2*padding), t_height-(2*padding))
            for (txt, xy, ftsz) in best_locations:
                write_text_to_img(img, (padding+xy[0], padding+xy[1]), txt, tfont, font_size=ftsz, color=text_color)

            #image
            insert1 = resize_and_crop(img1, ad_size[0]/2, i_height, crop=True, feather_percent=0.00)
            img.paste(insert1, (0, t_height), mask=feather_map(insert1.size, percent=0.00))

            insert2 = resize_and_crop(img2, ad_size[0]/2, i_height, crop=True, feather_percent=0.00)
            img.paste(insert2, (ad_size[0]/2, t_height), mask=feather_map(insert2.size, percent=0.00))

            #slogan
            extra_pad=5
            best_locations = optimal_text_splits(slogan, sfont, ad_size[0]-(2*(padding+extra_pad)), s_height-(padding))
            for (txt, xy, ftsz) in best_locations:
                write_text_to_img(img, (extra_pad+padding+xy[0], t_height+i_height+(padding//2)+xy[1]), txt, sfont, font_size=ftsz, color=text_color)

        else:
            #print 'normal no text'
            #image if no text around
            insert1 = resize_and_crop(img1, ad_size[0]/2, ad_size[1], crop=True, feather_percent=0.00)
            img.paste(insert1, (0, 0), mask=feather_map(insert1.size, percent=0.00))

            insert2 = resize_and_crop(img2, ad_size[0]/2, ad_size[1], crop=True, feather_percent=0.00)
            img.paste(insert2, (ad_size[0]/2, 0), mask=feather_map(insert2.size, percent=0.00))

            #slogan
            extra_pad=5
            best_locations = optimal_text_splits(slogan, sfont, ad_size[0]-(2*(padding+extra_pad)), s_height-(padding))
            for (txt, xy, ftsz) in best_locations:
                write_text_to_img(img, (extra_pad+padding+xy[0], t_height+i_height+(padding//2)+xy[1]), txt, sfont, font_size=ftsz, color=bk_color)

        img.save(os.path.join(output_folder, fname + '_' + str(ad_size[0]) + 'x' + str(ad_size[1]) + '.png'))

    else: #special case tall/skinny or wide

        if ad_size[0] < ad_size[1]:
            #tall skyscraper
            padding = 3 * ad_size[0] // 100

            if text is None:
                #print 'skyscrape no text'
                #fill image and put slogan at bottom
                t_height = 2 *ad_size[1] // 5
                s_height = ad_size[1] // 5

                #image
                insert1 = resize_and_crop(img1, ad_size[0], t_height, crop=True, feather_percent=0.00)
                img.paste(insert1, (0, 0), mask=feather_map(insert1.size, percent=0.00))

                insert2 = resize_and_crop(img2, ad_size[0], t_height, crop=True, feather_percent=0.00)
                img.paste(insert2, (0, t_height), mask=feather_map(insert2.size, percent=0.00))

                extra_pad=5
                best_locations = optimal_text_splits(slogan, sfont, ad_size[0]-(2*(padding+extra_pad)), s_height-(2*(padding+extra_pad)))
                for (txt, xy, ftsz) in best_locations:
                    write_text_to_img(img, (extra_pad+padding+xy[0], (2*t_height)+extra_pad+padding+xy[1]), txt, sfont, font_size=ftsz, color=text_color)

            else:
                #print 'skyscrape w text'
                # 2/5, 2/5, 1/5 fill image and put slogan at bottom
                s_height = ad_size[1] // 6

                #text
                best_locations = optimal_text_splits(text, tfont, ad_size[0]-(2*padding), (s_height)-(2*padding))
                for (txt, xy, ftsz) in best_locations:
                    write_text_to_img(img, (padding+xy[0], padding+xy[1]), txt, tfont, font_size=ftsz, color=text_color)

                #image
                insert1 = resize_and_crop(img1, ad_size[0], 2*s_height, crop=True, feather_percent=0.00)
                img.paste(insert1, (0, s_height), mask=feather_map(insert1.size, percent=0.00))

                insert2 = resize_and_crop(img2, ad_size[0], 2*s_height, crop=True, feather_percent=0.00)
                img.paste(insert2, (0, 3*s_height), mask=feather_map(insert2.size, percent=0.00))

                extra_pad=5
                best_locations = optimal_text_splits(slogan, sfont, ad_size[0]-(2*(padding+extra_pad)), s_height-(2*(padding+extra_pad)))
                for (txt, xy, ftsz) in best_locations:
                    write_text_to_img(img, (extra_pad+padding+xy[0], (5*s_height)+extra_pad+padding+xy[1]), txt, sfont, font_size=ftsz, color=text_color)

        else:
            #wide banner
            padding = 3 * ad_size[1] // 100

            if text is None:
                #print 'banner no text'

                #4/5 width for images 2/5 each, and 1/5 for slogan
                i_width = 2 * ad_size[0] // 5
                t_width = ad_size[0] // 5

                #image
                insert1 = resize_and_crop(img1, i_width, ad_size[1], crop=True, feather_percent=0.00)
                img.paste(insert1, (0, 0), mask=feather_map(insert1.size, percent=0.00))

                insert2 = resize_and_crop(img2, i_width, ad_size[1], crop=True, feather_percent=0.00)
                img.paste(insert2, (i_width, 0), mask=feather_map(insert2.size, percent=0.00))

                #slogan
                extra_pad=5
                best_locations = optimal_text_splits(slogan, sfont, t_width-(2*(padding+extra_pad)), (ad_size[1] //4)-(padding))
                for (txt, xy, ftsz) in best_locations:
                    write_text_to_img(img, (2*i_width + extra_pad+padding+xy[0], (3 * ad_size[1] // 4)+(padding//2)+xy[1]), txt, sfont, font_size=ftsz, color=text_color)

            else:
                #print 'banner w text'
                #split screen into fifths, 2/5 for image, 3/5 for text
                i_width = 2 * ad_size[0] // 5
                t_width = 3 * ad_size[0] // 5

                #image
                insert1 = resize_and_crop(img1, i_width/2, ad_size[1], crop=True, feather_percent=0.00)
                img.paste(insert1, (0, 0), mask=feather_map(insert1.size, percent=0.00))

                insert2 = resize_and_crop(img2, i_width/2, ad_size[1], crop=True, feather_percent=0.00)
                img.paste(insert2, (i_width/2, 0), mask=feather_map(insert2.size, percent=0.00))

                best_locations = optimal_text_splits(text, tfont, t_width-(2*padding), (3 * ad_size[1] // 4)-(2*padding))
                for (txt, xy, ftsz) in best_locations:
                    write_text_to_img(img, (i_width + padding + xy[0], padding+xy[1]), txt, tfont, font_size=ftsz, color=text_color)

                extra_pad=5
                best_locations = optimal_text_splits(slogan, sfont, t_width-(2*(padding+extra_pad)), (ad_size[1] //4)-(padding))
                for (txt, xy, ftsz) in best_locations:
                    write_text_to_img(img, (i_width + extra_pad+padding+xy[0], (3 * ad_size[1] // 4)+(padding//2)+xy[1]), txt, sfont, font_size=ftsz, color=text_color)


        img.save(os.path.join(output_folder, fname + '_' + str(ad_size[0]) + 'x' + str(ad_size[1]) + '.png'))

    #return filename of ad created
    return os.path.join(relative_output_folder, fname + '_' + str(ad_size[0]) + 'x' + str(ad_size[1]) + '.png')


def pairing_ad_wrapper(fname, image, text=None, slogan=None, sfont=None, happy=True:

    #ref to all happy images and partial pairing slogan 'puppy.png' ' makes puppies happy!'
    if happy:
        em_ads = [
                {'text':'is joy.','src': 'smiling.jpg'},
                {'text':'= kittens','src': 'kitten.jpg'},
                {'text':'totally rocks!','src': 'rocks.jpg'},
                {'text':'is wonderful','src': 'baby.jpg'},
                {'text':'makes puppies happy!','src': 'puppy.jpg'}
        ]
    else:
        em_ads = [
                {'text':'IS EVIL','src':'scary.jpg'},
                {'text':'causes sickness','src':'sick.jpg'},
                {'text':'hurts others','src':'begging.jpg'},
                {'text':'= DEATH','src':'skulls.jpg'},
        ]

    #gen in loop like ad_wrapper
    ad_files = []

    for adsize, dims in full_sizes.iteritems():
        for em_ad in em_ads:

            if text is not None:
                em_img = os.path.join(pairing_subfolder, em_ad['src'])
                ad_text = text + ' ' + em_ad['text']

                generated_file = pairing_ad_generator(dims, fname+em_ad['src'][:-4], image, em_img, ad_text, slogan, sfont)
                ad_files.append([dims, generated_file])

            generated_file = pairing_ad_generator(dims, fname+em_ad['src'][:-4]+'img', image, em_img, None, slogan, sfont)
            ad_files.append([dims, generated_file])

    return ad_files


def print_ad_advice():

    print ('\n' + '-'*80 +
          '\n ADVICE FOR AD CREATION: \n' +
          '-'*80 + '\n' +
          ' 1. Rational and emotional appeals are both effective, try to make ads of both types to support a single goal.\n' +
          ' 2. Negative-framing of ads is best to drive action, gain-framing is best for memorability. Use both framings.\n'
          ' 3. Varying ad types (image only, text, text/image) are useful to continue to attract attention, use all for your goal.\n' +
          ' 4. Longer ad text and blending colors in with a site (not too bright) actually works best to attract attention.\n' +
          ' 5. Attractive people work well for attraction-based changes like health behaviors, gym, diet, etc.\n' +
          ' 6. Try appealing to your identity. \'You are strong.  You are powerful.  That\'s why you go to the gym\'\n' +
          ' 7. Try behavior contracts. \'Click here if you agree to call your dad today!\'\n' +
          ' 8. Use direct commands, which are expected/useful in ads \'Do this now.\' \n' +
          ' 9. Use social priming/techniques.  Celebrities or suggestions that your friends are doing your target activity are good.\n' +
          '10. Use blatant pairing of things you have strong positive/negative emotions for with things you wish to have those reactions to.\n' +
          '11. Thin fonts convey beauty, obscure fonts convey uniqueness, slanted conveys speed.  Use them in relevant contexts.\n' +
          '12. Use reds for negative-framed ads and blues for gain-framed ads.\n' +
          '-'*80 + '\n'
    )


def commandline_ad_create():

    json_blob = get_json_blob()

    none_option = unicode('None')
    images = [none_option] + [os.path.split(f)[-1] for f in glob.glob(os.path.join(input_folder, '*')) if not os.path.isdir(f)]

    questions = [
        {
            'type': 'input',
            'name': 'name',
            'message': 'short, unique ad id:'
        },
        {
            'type': 'list',
            'name': 'campaign',
            'message': 'which campaign is this?',
            'choices': [c['slogan'] for c in json_blob['campaigns']]
        },
        {
            'type': 'input',
            'name': 'text',
            'message': 'ad text (i.e.: Go to the GYM!):'
        },
        {
            'type': 'input',
            'name': 'success',
            'message': 'text describing goal success (i.e.: You went to the gym!):'
        },
        {
            'type': 'list',
            'name': 'cadence',
            'message': 'how frequently should this ad be shown?',
            'choices': ['daily','bi-weekly','weekly','bi-monthly','monthly','quarterly','bi-annually']
        },
        {
            'type': 'list',
            'name': 'image',
            'message': 'which image?',
            'choices': images,
            'default': none_option
        },
        {
            'type': 'list',
            'name': 'pairing',
            'message': 'Is this an \'association\' ad?',
            'choices': ['No', 'Yes, pair it with happy concepts', 'Yes, pair it with sad concepts']
        }
    ]

    ad = prompt(questions)

    if ad['text'] in [none_option, unicode('')]: ad['text'] = None
    if ad['image'] == none_option: ad['image'] = None

    ad['last_accomplished'] = None
    ad['should_show'] = True

    selected_campaign = [c for c in json_blob['campaigns'] if c['slogan']==ad['campaign']][0]
    ad['campaign'] = selected_campaign

    if prompt({'type':'confirm','name':'confirm','message':'All looks good, make advertisement?','default':False})['confirm']:
        print 'generating ads ...'

        if ad['pairing'] is not 'No':
            assert(ad['image'] is not None), 'pairing ads must have an image'

            if 'happy' in ad['pairing']: happy=True
            else: happy=False

            ad['files'] = pairing_ad_wrapper(ad['name'] + 'pair',image=ad['image'],text=ad['text'], slogan=ad['campaign']['slogan'], sfont=ad['campaign']['sfont'], happy=happy)
        else:
            ad['files'] = ad_wrapper(ad['name'],text=ad['text'],slogan=ad['campaign']['slogan'],sfont=ad['campaign']['sfont'],image=ad['image'])

        print 'done. saving ...'
        json_blob['ads'].append(ad)
        save_json_blob(json_blob)
        print 'saved.'
    else:
        print 'ad aborted.'


def ad_server(port=8000):
    print 'starting ad server on port ' + str(port) + ' ...'
    httpd = SocketServer.TCPServer(('',port), SimpleHTTPServer.SimpleHTTPRequestHandler)
    httpd.serve_forever()


def ad_basic_walkthrough():

    f = Figlet(font='cybermedium')
    print f.renderText('YourAD CREATOR')

    selection = prompt({
        'type':'list',
        'name':'option',
        'message':'What would you like to do?',
        'choices': ['create ads','serve ads','exit']
        })['option']

    if selection =='create ads':
        print_ad_advice()
        confirm = True
        while confirm:
            commandline_ad_create()
            confirm = prompt({
                'type':'confirm',
                'name':'confirm',
                'message':'Would you like to make another advertisement?',
                'default':False}
                )['confirm']

    if selection != 'exit':
        print '\n' + '-'*50 + '\n -- STARTING AD SERVER -- \n' + '-'*50
        ad_server()


if __name__=='__main__':

    ad_basic_walkthrough()
