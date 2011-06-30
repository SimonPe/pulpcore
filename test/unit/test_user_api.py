#!/usr/bin/python
#
# Copyright (c) 2011 Red Hat, Inc.
#
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

# Python
import logging
import sys
import os
import time
import unittest
import uuid

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)) + "/../common/")
import testutil

class TestUsers(testutil.PulpAsyncTest):

    def test_create(self):
        clear_txt_pass = 'some password'
        user = self.user_api.create('login-test', id=str(uuid.uuid4()),
                                password=clear_txt_pass,
                                name='Fred Franklin')
        self.assertTrue(user is not None)
        user = self.user_api.user('login-test')
        self.assertTrue(user is not None)
        self.assertNotEqual(clear_txt_pass, user['password'])

    def test_duplicate(self):
        id = uuid.uuid4()
        login = 'dupe-test'
        user = self.user_api.create(login=login, id=id)
        try:
            user = self.user_api.create(login=login, id=id)
            raise Exception, 'Duplicate allowed'
        except:
            pass

    def test_user_list(self):
        user = self.user_api.create('login-test')
        users = self.user_api.users()
        assert(len(users) == 1)

    def test_clean(self):
        user = self.user_api.create('login-test')
        self.user_api.clean()
        users = self.user_api.users()
        assert(len(users) == 0)

    def test_delete(self):
        login = 'some-login'
        user = self.user_api.create(login)
        self.user_api.delete(login=login)
        user = self.user_api.user(login)
        assert(user is None)

    def test_update_password(self):
        login = 'some-login'
        clear_txt_pass = 'some password'
        user = self.user_api.create(login)
        d = dict(password=clear_txt_pass)
        user = self.user_api.update(login, d)

        # Lookup user again and verify password is hashed
        user = self.user_api.user(login)
        self.assertTrue(user is not None)
        self.assertTrue(user['password'] is not None)
        self.assertNotEqual(clear_txt_pass, user['password'])


if __name__ == '__main__':
    logging.root.addHandler(logging.StreamHandler())
    logging.root.setLevel(logging.ERROR)
    unittest.main()
