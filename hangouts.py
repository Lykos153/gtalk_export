import re
import json
import time

# This code was inspired by Jay2K1's Hangouts parser.  You can see the 
# blogpost for the original at:
# http://blog.jay2k1.com/2014/11/10/how-to-export-and-backup-your-google-hangouts-chat-history/
# He also runs a webservice for parsing Google Hangouts JSON files at:
# http://hangoutparser.jay2k1.com/

def hangoutsToArray(json_input, timestamp_format):
    # set the desired timestamp format here
    # the default is '%Y-%m-%d %H:%M:%S' which is YYYY-MM-DD HH:mm:ss.
    #timestamp_format = '%Y-%m-%d %H:%M:%S'

    # decode JSON
    decoded = json.loads(json_input)
    # extract useful part
    rawconvos = decoded['conversation_state']
    #print "%r" % rawconvos
    retval = []
    # loop through conversations
    for i in range(len(rawconvos)):
        #print "i is %d" % i
        #print "attempting in_conv: %s" % rawconvos[i]['conversation_state']['conversation']
        # first, get metadata
        retval.append({})
        convo = rawconvos[i]
        #print "%r" % convo
        in_conv = rawconvos[i]['conversation_state']['conversation']
        in_event = rawconvos[i]['conversation_state']['event']
        pdata = in_conv['participant_data']
        retval[i]['id'] = in_conv['id']['id']
        retval[i]['type'] = in_conv['type']
        retval[i]['msgcount'] = len(in_event)
        retval[i]['name'] = in_conv['name'] if 'name' in in_conv.keys() else ""
        # conversation participants
        for j in range(len(pdata)):
            id = pdata[j]['id']['chat_id']
            # use "unknown_<chat_id>" as name if they don't have a fallback_name
            name = pdata[j]['fallback_name'] if 'fallback_name' in pdata[j].keys() else "unknown_%s" % id
            if not 'members' in retval[i].keys():
                retval[i]['members'] = {}
            retval[i]['members'][id] = name

        # loop through messages/events
        messages = []
        for k in range(len(in_event)):
            messages.append({})
            messages[k]['timestamp'] = in_event[k]['timestamp']
            messages[k]['datetime'] = time.strftime(timestamp_format,time.localtime(int(messages[k]['timestamp'][0:10])))
            messages[k]['sender_id'] = in_event[k]['sender_id']['chat_id']
            messages[k]['sender'] = retval[i]['members'][messages[k]['sender_id']] if messages[k]['sender_id'] in retval[i]['members'].keys() else "unknown_%s" % id
            messages[k]['event_type'] = in_event[k]['event_type']
            messages[k]['event_id'] = in_event[k]['event_id']

            if messages[k]['event_type'] == 'RENAME_CONVERSATION':
                newname = in_event[k]['conversation_rename']['new_name']
                oldname = in_event[k]['conversation_rename']['old_name']
                messages[k]['message'] = "changed conversation name %s%s" % \
                                         (("from '%s'" % oldname) if oldname else "", 
                                          ("to '%s'" % newname) if newname else "")
            elif messages[k]['event_type'] == 'HANGOUT_EVENT':
                if in_event[k]['hangout_event']['event_type'] == 'START_HANGOUT':
                    messages[k]['message'] = 'started a video chat'
                elif in_event[k]['hangout_event']['event_type'] == 'END_HANGOUT':
                    messages[k]['message'] = 'ended a video chat'
                else:
                    messages[k]['message'] = in_event[k]['hangout_event']['event_type']
            elif messages[k]['event_type'] == 'REGULAR_CHAT_MESSAGE':
                messages[k]['message'] = ""
                msg = ""
                msghtml = ""
                # join message segments together
                if 'segment' in in_event[k]['chat_message']['message_content'].keys():
                    for event in in_event[k]['chat_message']['message_content']['segment']:
                        if not 'text' in event.keys():
                            continue
                        if event['type'] == 'TEXT':
                            msg += event['text']
                            msghtml += re.sub("\n", "<br>", event['text'])
                        elif event['type'] == 'LINK':
                            msg += event['text']
                            msghtml += '<a href="%s" target="_blank">%s</a>' % (event['link_data']['link_target'], event['text'])
                        elif event['type'] == 'LINE_BREAK':
                            msg += event['text']
                            msghtml += re.sub("\n", "<br>", event['text'])
                # handle attachments
                elif 'attachment' in in_event[k]['chat_message']['message_content'].keys():
                    # loop through attachments
                    for att in in_event[k]['chat_message']['message_content']['attachment']:
                        # echo "<pre>";print_r($att);echo "</pre>";
                        if att['embed_item']['type'][0] == 'PLUS_PHOTO':
                            imgurl = att['embed_item']['embeds.PlusPhoto.plus_photo']['url']
                            msg += imgurl
                            msghtml += '<a href="%s" target="_blank"><img src="%s" alt="attached image" style="max-width:%s"></a>' % (imgurl, imgurl, "100%")
                messages[k]['message'] = msg
                if msg != msghtml:
                    messages[k]['message_html'] = msghtml
            elif messages[k]['event_type'] == 'ADD_USER':
                newuserid = in_event[k]['membership_change']['participant_id'][0]['chat_id']
                newusername = retval[i]['members'][newuserid] if newuserid in retval[i]['members'].keys() else 'unknown_%s' % newuserid
                messages[k]['message'] = "added user '%s' to conversation" % newusername
            elif messages[k]['event_type'] == 'REMOVE_USER':
                newuserid = in_event[k]['membership_change']['participant_id'][0]['chat_id']
                newusername = retval[i]['members'][newuserid] if newuserid in retval[i]['members'].keys() else 'unknown_%s' % newuserid
                messages[k]['message'] = "removed user '%s' from conversation" % newusername
            elif messages[k]['event_type'] == 'SMS':
                messages[k]['message'] = ""
                # join message segments together
                if 'segment' in in_event[k]['chat_message']['message_content'].keys():
                    for l in range(len(in_event[k]['chat_message']['message_content']['segment'])):
                        if not 'text' in in_event[k]['chat_message']['message_content']['segment'][l].keys():
                            continue
                        messages[k]['message'] += in_event[k]['chat_message']['message_content']['segment'][l]['text']
            elif messages[k]['event_type'] == 'OTR_MODIFICATION':
                messages[k]['message'] = 'unknown OTR_MODIFICATION'
            elif messages[k]['event_type'] == 'VOICEMAIL':
                messages[k]['message'] = "new voicemail:\n"
                # join message segments together
                if 'segment' in in_event[k]['chat_message']['message_content'].keys():
                    for l in range(len(in_event[k]['chat_message']['message_content']['segment'])):
                        if not 'text' in in_event[k]['chat_message']['message_content']['segment'][l].keys():
                            continue
                        messages[k]['message'] += in_event[k]['chat_message']['message_content']['segment'][l]['text']
        # sort messages by timestamp because for some reason they're cluttered
        messages.sort(key=lambda message: message['timestamp'])
        # add the messages array to the conversation array
        retval[i]['messages'] = messages
    return retval
