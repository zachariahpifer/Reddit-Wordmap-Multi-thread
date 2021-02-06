import logging, string
from PIL import Image
import threading
import time, praw
import queue
import pandas as pd
from wordcloud import WordCloud, STOPWORDS, ImageColorGenerator
import matplotlib.pyplot as plt
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
import numpy as np

# Create write queue
write_q = queue.Queue()

class Comments:
    def __init__(self, name):
        self.ids = []
        self.sub_ids = []
        self.scores = {'name': name}
        self.counts = {'name': name}
        self.words = []
        self._lock_words = threading.Lock()
        self._lock_ids = threading.Lock()
        self._lock_sub_ids = threading.Lock()
        self._lock_scores = threading.Lock()
    
    def check_id(self, id):
        with self._lock_ids:
            if id not in self.ids:
                self.ids.append(id)
                return 0
            else:
                return 1
    
    def check_submis_id(self, id):
        with self._lock_sub_ids:
            if id not in self.sub_ids:
                self.sub_ids.append(id)
                return 0
            else:
                return 1

    def check_keys(self, key):
        with self._lock_scores:
            if key not in self.scores.keys():
                return 0
            else:
                return 1
    
    def add_subreddit(self, subreddit, score):
        with self._lock_scores: 
            local_copy = self.scores
            local_copy[subreddit] = score
            self.scores = local_copy
            local_copy = self.counts
            local_copy[subreddit] = 1
            self.counts = local_copy

    def update_subreddit(self, subreddit, score):
        with self._lock_scores:
            local_copy = self.scores
            local_copy[subreddit] += score
            self.scores = local_copy
            local_copy = self.counts
            local_copy[subreddit] += 1
            self.counts = local_copy
    
    def get_scores(self): return self.scores
    def get_words(self): return self.words
    def get_counts(self): return self.counts

    def add_words(self, body):
        with self._lock_words:
            self.words.append(body)

# unique reddit instance for each thread
reddit_0 = praw.Reddit(client_id='a8fxlGxtt5HeRg', client_secret='x0oQ53axICf_azi5SY_yB5xVkE8', user_agent='Reddit Scrape')
reddit_1 = praw.Reddit(client_id='jEls41W7AHDIsA', client_secret='L-5CC9ROoIYS01U7wTERr4Wsho0', user_agent='Reddit Scrape 1')
reddit_2 = praw.Reddit(client_id='jsxwWoXt-7OKeg', client_secret='9UJRPJDNq5OAJN6Rf8TWCbCoG7w', user_agent='Reddit Scrape 2')

reddit_ints = [reddit_0, reddit_1, reddit_2]

# Define Read Thread function
def read_thread_function(instance, user, sort, comments):
    # Initialize Things
    redditor = instance.redditor(user)
    comment_sorts = [redditor.comments.new(limit=None), redditor.comments.top(limit=None), redditor.comments.controversial(limit=None)]
    submission_sorts = [redditor.submissions.new(limit=None), redditor.submissions.top(limit=None), redditor.submissions.controversial(limit=None)]
    count = 0

    # Get comments
    for redditor_comment in comment_sorts[sort]:
        if comments.check_id(redditor_comment.id):
            count+=1

            # Add subreddit scores
            if comments.check_keys(redditor_comment.subreddit.display_name):
                try: comments.update_subreddit(redditor_comment.subreddit.display_name,redditor_comment.score)
                except: None
            else:
                try: comments.add_subreddit(redditor_comment.subreddit.display_name,redditor_comment.score)
                except: None
            
            # Add words
            comments.add_words(redditor_comment.body)

    print("Comments retreived: " +str(count) + "\n")

    # Get Submissions
    for redditor_submission in submission_sorts[sort]:
        if comments.check_submis_id(redditor_submission.id):
            comments.add_words(redditor_submission.title)
            comments.add_words(redditor_submission.selftext)

def write_thread_function():
    while True:
        item = write_q.get()
        print("Writing item")
        scores.append(item, ignore_index=True)
        write_q.task_done()

def pre_process_words(word_list):
    words = ' '.join(word_list).translate(str.maketrans('', '', string.punctuation)).lower().split()
    stops = set(stopwords.words('english'))
    stops = stops.union({'people', 'think', 'that', 'im', 'dont','one','year','much','time','know'})
    new_words = [word for word in words if word not in stops]
    new_words = ' '.join(new_words)
    return new_words

if __name__ == "__main__":
    format = "%(asctime)s: %(message)s"
    logging.basicConfig(format=format, level=logging.INFO, datefmt="%H:%M:%S")

    user = 'zaxldaisy'
    threads = list()
    start = time.time() # start time
    comments = Comments(user)

    # threading.Thread(target=write_thread_function, daemon=True).start()
    
    for index in range(3):
        logging.info("Main    : create and start thread %d.", index)
        # Each thread does different sort call
        x = threading.Thread(target=read_thread_function, args=(reddit_ints[index], user, index, comments))
        threads.append(x)
        x.start()

    for index, thread in enumerate(threads):
        thread.join()
    
    # print(comments.counts)

    print("Time elapsed: ", (time.time() - start)) # end time
    # write_q.join()

    temp = comments.get_words()
    processed_words = pre_process_words(temp)

    wordcloud = WordCloud(collocations=False, background_color="white", max_words=300, width=500, height=500).generate(processed_words)

    plt.imshow(wordcloud, interpolation='bilinear')
    plt.axis("off")
    plt.show()