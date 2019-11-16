# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.shortcuts import render
from bs4 import BeautifulSoup
from bs4.element import Comment
from urllib import urlopen
from urlparse import urlparse
import re
# Create your views here.
from django import forms

from keras.preprocessing.image import img_to_array
from keras.models import load_model
import numpy as np
import argparse
import imutils
import cv2
import os
import requests
import shutil

from nltk.stem.porter import PorterStemmer
from nltk.corpus import stopwords
import nltk


class sitelink(forms.Form):
    link = forms.CharField()
    crawllength = forms.IntegerField()
    def sendlink(self):
        return self.link
    
def classify_images():
    model = load_model(str("guns.model"))
    images = os.listdir("./images")
    print(images)
    prediction= []
    perc=0
    for img in images:
        #try:
        image = cv2.imread("./images/"+img)
        print("read "+img)
        image = cv2.resize(image, (224, 224))
        image = image.astype("float") / 255.0
        image = img_to_array(image)
        image = np.expand_dims(image, axis=0)
        (k,p) = model.predict(image)[0]
        print(p)
        prediction.append(p)
        #except:
         #   print("not able to read "+img)
          #  continue
    print(prediction)
    for pred in prediction:
        if pred>0.95:
            perc+=1
    try:
        return perc*100/len(prediction)
    except:
        return "NA"
    
def tag_visible(element):
    if element.parent.name in ['style', 'script', 'head', 'title', 'meta', '[document]']:
        return False
    if isinstance(element, Comment):
        return False
    
    return True


def download_images(images):
    shutil.rmtree("./images")
    os.mkdir("./images")
    total = 0
    for url in images:
        try:
            r = requests.get(url, timeout=60)

            # save the image to disk
            p = os.path.sep.join(["./images", "{}.jpg".format(
                str(total).zfill(8))])
            f = open(p, "wb")
            f.write(r.content)
            f.close()

            # update the counter
            print("[INFO] downloaded: {}".format(p))
            total += 1

        # handle if any exceptions are thrown during the download process
        except:
            print("[INFO] error downloading {}...skipping".format(p))

def text_cleaner(text):
    
    words = nltk.word_tokenize(text)
    words = [word.lower() for word in words if word.isalpha()]
    # table = str.maketrans('', '', string.punctuation)
    # words = [word.translate(table) for word in words]
    words = [word for word in words if word.isalpha()]
    
    
    stop_words = set(stopwords.words('english'))
    words = [word for word in words if not word in stop_words]
    
    porter = PorterStemmer()
    words = [porter.stem(word) for word in words]
    cleaned_text = ' '.join(words)
    
    return cleaned_text



def text_analyser(text):
    text  = text_cleaner(text)
    text = text.split()
    count = 0

    word_corpus = ['hate', 'shoot', 'kill', 'murder', 'muslim', 'terror', 'christian', 'hindu', 'jihad', 'jihadi', 'nigga', 'negro', 'bomb', 'loot', 'rape', 'whitey','gun']
    word_corpus = set(word_corpus)
    for word in text:
        if word in word_corpus:
            count+=1
    try:
        score = count*1000/len(text)
    except:
        return "NA"
    print(count)
    return min(score,100)


def website_analyser(pagelink):
    try:
        html = urlopen(pagelink)
    except:
        return None
    bs = BeautifulSoup(html, 'html.parser')
    #print(bs)
    images = bs.find_all('img', {'src':re.compile('.jpg')})
    links = bs.find_all('a',href = True)
    
    images = [image['src'] for image in images]
    final_images = []
    for img in images:
        if len(img)>10:
            if img[:4]!="http":
                if img[:2]=="//":
                    final_images.append("https:"+img)
                elif img[0]=="/":
                    final_images.append("https:/"+img)
                else:
                    final_images.append("https://"+img)
            else:
                final_images.append(img)
    images = final_images
    links = [urlparse(link['href']).netloc for link in links]
    links = list(set(links))
    final_links = []
    for link in links:
        if len(link)>10:
            if link[:4]!="http":
                final_links.append("https://"+link)
            else:
                final_links.append(link)
    links = final_links
    download_images(images)
    text = bs.findAll(text=True)
    text = filter(tag_visible, text)
    text = u" ".join(t.strip() for t in text)
    arms_image = classify_images()
    hate_speech_score = text_analyser(text)

    return pagelink,links,images,text,arms_image,hate_speech_score


def index(request):
    
    if request.method == 'POST':
        form = sitelink(request.POST)
        pagelink = form['link'].value()
        crawllength = form['crawllength'].value()
        crawllength = int(crawllength)
        #crawllength = 5
        print(pagelink)
        # result = website_analyser(pagelink)
        # if result==None:
        #     return render(request,'home.html',{})
        analysed_links = set()
        q = [pagelink]
        results = []
        while len(q)>0 and crawllength>0:
            print(q)
            crawllength-=1
            currlink = q[0]
            q.pop(0)
            if currlink in analysed_links:
                continue
            result = website_analyser(currlink)
            analysed_links.add(currlink)
            
            if result!=None:
                pagelink,links,images,text,arms_image,hate_speech_score = result
                result = (pagelink,len(links),len(images),len(text.split()),arms_image,hate_speech_score)
                results.append(list(result))
                print(result)
                #if hate_speech_score>10:
                q.extend(links)
            else:

                return render(request,'home.html',{})
        return render(request,'home.html',{'results':results,'crawllength':len(results),'mainlink' :results[0]})
    else:
        return render(request,'home.html',{})
    
    

'''
from bs4 import BeautifulSoup
from bs4.element import Comment
import urllib


def tag_visible(element):
    if element.parent.name in ['style', 'script', 'head', 'title', 'meta', '[document]']:
        return False
    if isinstance(element, Comment):
        return False
    elif re.match(r"[\s\r\n]+",str(element)):
        return False
    return True


def text_from_html(body):
    soup = BeautifulSoup(body, 'html.parser')
    texts = soup.findAll(text=True)
    visible_texts = filter(tag_visible, texts)  
    return u" ".join(t.strip() for t in visible_texts)

html = urllib.urlopen('http://www.nytimes.com/2009/12/21/us/21storm.html').read()
print(text_from_html(html))

'''
