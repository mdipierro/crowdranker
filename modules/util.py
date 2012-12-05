#!/usr/bin/env python
# coding: utf8
from gluon import *
import re

email_split_pattern = re.compile('[,\s]+')
whitespace = re.compile('\s+')

def union_id_list(l1, l2):
    """Computes the union of the 'id' elements of two lists of dictionaries."""
    id1l = [el['id'] for el in l1]
    id2l = [el['id'] for el in l2]
    for id in id2l:
        if not (id in id1l):
            id1l.append(id)
    return id1l
    
def list_append_unique(l, el):
    """Appends an element to a list, if not present."""
    if l == None:
        return [el]
    if el in l:
        return l
    else:
        return l + [el]
                
def list_remove(l, el):
    """Removes element el from list l, if found."""
    if l == None:
        return []
    if el not in l:
        return l
    else:
        l.remove(el)
        return l
        
def list_diff(l1, l2):
    if l1 == None:
        l1 = []
    if l2 == None:
        l2 = []
    r = []
    for el in l1:
        if el not in l2:
            r += [el]
    return r
        
def split_emails(s):
    """Splits the emails that occur in a string s, returning the list of emails."""
    l = email_split_pattern.split(s)
    if l == None:
        return []
    else:
        r = []
        for el in l:
            if len(el) > 0 and not whitespace.match(el):
                r += [el]
        return r

def normalize_email_list(l):
    if isinstance(l, basestring):
        l = [l]
    r = []
    for el in l:
        ll = split_emails(el)
        r += ll
    return r