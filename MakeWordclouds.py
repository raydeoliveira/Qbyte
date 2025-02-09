# -*- coding: utf-8 -*-
"""
Created on Tue May  3 01:22:13 2022

@author: Danny
"""
from wordcloud import WordCloud, STOPWORDS
import matplotlib.pyplot as plt
import numpy as np
import random
import os
import sys

outpath = os.getcwd()
name = sys.argv[1]
infile = sys.argv[2]

words = []
special_words = []
special_rgb = []
special_size = []

readfile = open(f'{outpath}/{infile}', 'r')
lines = readfile.read().split('\n')
for a in range(0, len(lines)):
    if 'QBYTE' in lines[a]:
        x_and_y = lines[a].split(',')
        time = int(x_and_y[-2])
        words.append(x_and_y[-1][8:])
    if 'color' in lines[a] and '|' not in lines[a]:
        x_and_y = lines[a].split(',')
        special_words.append(words[-1])
        special_rgb.append(f'rgb({int(x_and_y[3])},{int(x_and_y[4])},{int(x_and_y[5])})')
        special_size.append(int(float(x_and_y[6])))

# make decoy words:
all_words = []
readfile = open(f'{outpath}/Wordbank.txt', encoding='latin-1')
lines = readfile.read().split('\n')
for line in range(0, len(lines)):
    all_words.append(lines[line])

decoy = []
for a in range(0, len(words)):
    decoy_idx = np.random.randint(0, 196608)
    decoy.append(all_words[decoy_idx])

"""

coinflip = np.random.randint(0,2)
if coinflip==1:
    LabelFile = ['A','B']
else:
    LabelFile = ['B','A']
    
outfile = open('%s/%s_Wordlist%s.txt'%(outpath,name,LabelFile[0]),'w')
for a in range (0,len(words)):
    outfile.write('%s\n'%words[a])
outfile.close()

outfile = open('%s/%s_Wordlist%s.txt'%(outpath,name,LabelFile[1]),'w')
for a in range (0,len(decoy)):
    outfile.write('%s\n'%decoy[a])
outfile.close()

outfile = open('%s/%s_Target.txt'%(outpath,name),'w')
outfile.write('Target: %s\nDecoy: %s'%(LabelFile[0],LabelFile[1]))
outfile.close()

"""

# make decoy colors:

readFile = open('%s/DecoyColorSims.txt'%(outpath),'r')
lines = readFile.read().split('\n')
DecoyRGB=[]
DecoySize=[]
for a in range (0,len(lines)):
    xandy = lines[a].split(',')
    DecoyRGB.append('rgb(%d,%d,%d)'%(int(xandy[0]),int(xandy[1]),int(xandy[2])))
    DecoySize.append(int(float(xandy[3])))
    
DeWords = []
DeRGB = []
DeSize = []
for a in range (0,len(special_words)):
    LclDecoyIdx = np.random.randint(0,len(decoy))
    LclRGBIdx = np.random.randint(0,len(DecoyRGB))
    DeWords.append(decoy[LclDecoyIdx])
    DeRGB.append(DecoyRGB[LclRGBIdx])
    DeSize.append(DecoySize[LclRGBIdx])
    

# make target wordcloud:

def my_color_func(word, font_size, position, orientation, random_state=None, **kwargs):
    rcolor = 'rgb(255,255,255)'
    for a in range (0,len(special_words)):
        if special_words[a]==word:
            rcolor = special_rgb[a]
    return rcolor

    

stopwords = set(STOPWORDS)

my_words = []
for a in range (0,len(special_words)):
    for b in range (0,special_size[a]):
        my_words.append(special_words[a])
for a in range (0,len(words)):
    my_words.append(words[a])
random.shuffle(my_words)
wordtext = ''
for a in range (0,len(my_words)):
    wordtext += ' %s'%my_words[a]

wordcloud_target = WordCloud(width = 800, height = 800,
                background_color ='black',
                stopwords = stopwords,
                color_func = my_color_func,
                max_words = 100,
                ).generate(wordtext)

# make decoy wordcloud:

def my_color_decoy(word, font_size, position, orientation, random_state=None, **kwargs):
    rcolor = 'rgb(255,255,255)'
    for a in range (0,len(DeWords)):
        if DeWords[a]==word:
            rcolor = DeRGB[a]
    return rcolor

    

stopwords = set(STOPWORDS)

my_decoy = []
for a in range (0,len(DeWords)):
    for b in range (0,DeSize[a]):
        my_decoy.append(DeWords[a])
for a in range (0,len(decoy)):
    my_decoy.append(decoy[a])
random.shuffle(my_decoy)
wordtextD = ''
for a in range (0,len(my_decoy)):
    wordtextD += ' %s'%my_decoy[a]

wordcloud_decoy = WordCloud(width = 800, height = 800,
                background_color ='black',
                stopwords = stopwords,
                color_func = my_color_decoy,
                max_words = 100,
                ).generate(wordtextD)
 
# plot the WordCloud image                      
fig = plt.figure(figsize = (17, 8), facecolor = None)
ax1 = fig.add_subplot(121)
ax2 = fig.add_subplot(122)

coinflip = np.random.randint(0,2)
if coinflip==1:
    LabelFile = 'Target = RIGHT / B'
    ax1.imshow(wordcloud_decoy)
    ax2.imshow(wordcloud_target)
else:
    LabelFile = 'Target = LEFT / A'
    ax1.imshow(wordcloud_target)
    ax2.imshow(wordcloud_decoy)
    
outfile = open('%s/%s_Target.txt'%(outpath,name),'w')
outfile.write('%s'%LabelFile)
outfile.close()

ax1.axis("off")
ax2.axis("off")
plt.tight_layout(pad = 0)

plt.savefig('%s/%s.png'%(outpath,name))

#plt.show()



#decoy bank single file where randomly selects start time and continues until has same amount of special words
