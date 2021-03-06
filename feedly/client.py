# -*- encoding: utf-8 -*-
# For reference: https://developer.feedly.com/v3/

import json
import requests
import warnings

def json_fetch(url, method, params={}, data={}, headers={}):
    response = requests.request(method, url,
                                params=params,
                                data=json.dumps(data),
                                headers=headers)
    return response.json()

class FeedlyClient(object):
    ## INIT
    def __init__(self, **options):
        self.client_id = options.get('client_id')
        self.client_secret = options.get('client_secret')
        self.sandbox = options.get('sandbox', True)
        if self.sandbox:
            default_service_host = 'sandbox.feedly.com'
        else:
            default_service_host = 'cloud.feedly.com'
        self.service_host = options.get('service_host', default_service_host)
        self.additional_headers = options.get('additional_headers', {})
        self.token = options.get('token')
        self.secret = options.get('secret')

        self.info_urls = {
            'preferences': '/v3/preferences',
            'categories': '/v3/categories',
            'topics': '/v3/topics',
            'tags': '/v3/tags',
            'subscriptions': '/v3/subscriptions',
            'markers': '/v3/markers',
            'entries': '/v3/entries'
        }

    ## USER PROFILE & SUBSCRIPTIONS
    def get_user_profile(self, access_token):
        """
        return user's profile
        :param access_token:
        :return:
        """
        headers = {
            'content-type': 'application/json',
            'Authorization': 'OAuth ' + access_token
        }
        request_url = self._get_endpoint('/v3/profile')

        return json_fetch(request_url, "get", headers=headers)

    def get_code_url(self, callback_url):
        """

        :param callback_url:
        :return:
        """
        scope = 'https://cloud.feedly.com/subscriptions'
        response_type = 'code'

        request_url = '%s?client_id=%s&redirect_uri=%s&scope=%s&response_type=%s' % (
            self._get_endpoint('v3/auth/auth'), self.client_id, callback_url,
            scope, response_type)
        return request_url

    def get_access_token(self, redirect_uri, code):
        """

        :param redirect_uri:
        :param code:
        :return:
        """
        params = dict(client_id=self.client_id,
                      client_secret=self.client_secret,
                      grant_type='authorization_code',
                      redirect_uri=redirect_uri,
                      code=code)

        quest_url = self._get_endpoint('v3/auth/token')
        res = requests.post(url=quest_url, params=params)
        return res.json()

    def refresh_access_token(self, refresh_token):
        """
        obtain a new access token by sending a refresh token to the feedly Authorization server
        :param refresh_token:
        :return:
        """

        params = dict(refresh_token=refresh_token,
                      client_id=self.client_id,
                      client_secret=self.client_secret,
                      grant_type='refresh_token', )
        quest_url = self._get_endpoint('v3/auth/token')
        res = requests.post(url=quest_url, params=params)
        return res.json()

    def get_user_subscriptions_opml(self, access_token):
        """
        return user subscriptions in opml format
        :param access_token:
        :return:
        """
        return self._get_response(access_token, "/v3/opml").text

    def get_user_subscriptions(self, access_token):
        """
        return list of user subscriptions
        :param access_token:
        :return:
        """
        return self.get_info_type(access_token, 'subscriptions')


    ## FEEDS & ARTICLES
    def get_feed_content(self, access_token, streamId,
                         unreadOnly=None,
                         newerThan=None,
                         count=None,
                         continuation=None,
                         ranked=None):
        """
        return contents of a feed
        :param access_token:
        :param streamId:
        :param unreadOnly:
        :param newerThan:
        :param count:
        :param continuation:
        :param ranked:
        :return:
        """

        headers = {'Authorization': 'OAuth ' + access_token}
        quest_url = self._get_endpoint('v3/streams/contents')
        params = dict(streamId=streamId)
        # Optional parameters
        if unreadOnly is not None:
            params['unreadOnly'] = unreadOnly
        if newerThan is not None:
            params['newerThan'] = newerThan
        if count is not None:
            params['count'] = count
        if continuation is not None:
            params['continuation'] = continuation
        if ranked is not None:
            params['ranked'] = ranked
        res = requests.get(url=quest_url, params=params, headers=headers)
        return res.json()

    def mark_article_read(self, access_token, entryIds):
        """
        Mark one or multiple articles as read
        :param access_token:
        :param entryIds:
        :return:
        """
        headers = {
            'content-type': 'application/json',
            'Authorization': 'OAuth ' + access_token
        }
        quest_url = self._get_endpoint('v3/markers')
        params = dict(action="markAsRead", type="entries", entryIds=entryIds, )
        res = requests.post(url=quest_url,
                            data=json.dumps(params),
                            headers=headers)
        return res

    def mark_article_unsaved(self, access_token, entryIds):
        headers = {'content-type': 'application/json',
                   'Authorization': 'OAuth ' + access_token
                   }
        request_url = self._get_endpoint('v3/markers')
        params = dict(
            action="markAsUnsaved",
            type="entries",
            entryIds=entryIds,
        )
        res = requests.post(url=request_url, data=json.dumps(params), headers=headers)
        return res    
    
    def save_for_later(self, access_token, user_id, entryIds):
        """
        saved for later.entryIds is a list for entry id
        :param access_token:
        :param user_id:
        :param entryIds:
        :return:
        """
        headers = {
            'content-type': 'application/json',
            'Authorization': 'OAuth ' + access_token
        }
        request_url = self._get_endpoint(
            'v3/tags') + '/user%2F' + user_id + '%2Ftag%2Fglobal.saved'

        params = dict(entryIds=entryIds)
        res = requests.put(url=request_url,
                           data=json.dumps(params),
                           headers=headers)
        return res
    
    def get_entry_content(self, entryId):
        request__url = self._get_endpoint("v3/entries/" + entryId)
        res = requests.get(url=request__url).json()
        return res
    
    def get_entries_content(self, entryId):
        """Get data for all hashes in entryId.
        Note: API call is limited to 1000 hashes.
        """
        request__url = self._get_endpoint("v3/entries/" + ".mget")
        if len(entryId) > 1000:
            warnings.warn('This API call is limited to 1000 ids. Input will be restricted.')
            entryId = entryId[0:1000]
        res = requests.post(url=request__url, data=json.dumps(entryId)).json()
        return res

    def get_user_read(self, access_token, newerThan=None):
        """Get latest read operations. Default for API calls is 30 days.

        Input:
            newerThan: timestamp in ms (optional, default None)
        """
        headers = {'Authorization': 'OAuth ' + access_token}
        request__url = self._get_endpoint("v3/markers/reads")
        params={}
        if newerThan is not None:
            params['newerThan'] = newerThan
        res = requests.get(url=request__url, data=params, headers=headers)
        return res.json()

    # Categories
    def get_categories(self, access_token):
        """
        Returns the user's categories 
        """
        headers = {'Authorization': 'OAuth ' + access_token}
        request__url = self._get_endpoint("v3/categories")
        res = requests.get(url=request__url, headers=headers)
        return res.json()

    def get_sorted_categories(self,access_token):
        """
        Returns the user's categories in the same order as they appear in Feedly
        """
        headers = {'Authorization': 'OAuth ' + access_token}
        request__url = self._get_endpoint("v3/categories?sort=feedly")
        res = requests.get(url=request__url, headers=headers)
        return res.json()

    def change_category_label(self, access_token, categoryId, categoryLabel):
        """
        Change the label of an existing category. categoryId should be URLencoded
        """
        headers = {'Authorization': 'OAuth ' + access_token}
        request__url = self._get_endpoint("v3/categories/" + categoryId)
        params = dict(
            label=categoryLabel,
        )
        res = requests.post(url=request__url, data=json.dumps(params), headers=headers)
        return res

    def delete_category(self, access_token, categoryId):
        """
        Delete a category. Content will be moved to “global.uncategorized” category automatically. System categories cannot be deleted.
        """
        headers = {'Authorization': 'OAuth ' + access_token}
        request__url = self._get_endpoint("v3/categories/" + categoryId)
        res = requests.delete(url=request__url, headers=headers)
        return res

    # User preferences
    def get_user_preferences(self, access_token):
        """
        Get the preferences of the user. Preferences are application specific.
        Applications can not share preferences.
        """
        headers = {
            'Authorization': 'OAuth ' + access_token
        }
        request__url = self._get_endpoint("v3/preferences")
        res = requests.get(url=request__url, headers=headers)
        return res.json()

    def update_user_preferences(self, access_token, newprefs, newprefvalue):
        """
        Update the preferences of the user
        """
        headers = {
            'content-type': 'application/json',
            'Authorization': 'OAuth ' + access_token
        }
        request__url = self._get_endpoint("v3/preferences")
        params = dict(
            newprefs=newprefvalue,
        )
        res = requests.post(url=request__url, data=json.dumps(params), headers=headers)
        return res

    def delete_user_preference(self, access_token, pref):
        """
        Delete a specific preference by assigning the special "==DELETE==" value.
        """
        headers = {
            'content-type': 'application/json',
            'Authorization': 'OAuth ' + access_token
        }
        request__url = self._get_endpoint("v3/preferences")
        params = dict(
            pref="==DELETE==",
        )
        res = requests.post(url=request__url, data=json.dumps(params), headers=headers)
        return res
    
    ## GENERAL
    def _get_endpoint(self, path=None):
        """
        :param path:
        :return:
        """
        url = "https://%s" % self.service_host
        if path is not None:
            url += "/%s" % path
        return url
    
    def _get_response(self, access_token, url_endpoint):
        headers = {'Authorization': 'OAuth ' + access_token}
        quest_url = self._get_endpoint(url_endpoint)
        return requests.get(url=quest_url, headers=headers)

    def _get_info(self, access_token, url_endpoint):
        return self._get_response(access_token, url_endpoint).json()

    def get_info_type(self, access_token, type):
        if type in self.info_urls.keys():
            return self._get_info(access_token, self.info_urls.get(type))
