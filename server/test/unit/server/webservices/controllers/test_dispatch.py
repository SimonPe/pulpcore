"""
This module contains tests for the pulp.server.webservices.dispatch module.
"""
from datetime import datetime
import json
import uuid

import mock

from .... import base
from pulp.common import constants
from pulp.devel.unit.server.base import PulpWebservicesTests
from pulp.devel.unit.util import compare_dict
from pulp.server.async.task_status_manager import TaskStatusManager
from pulp.server.auth import authorization
from pulp.server.db.model.dispatch import TaskStatus
from pulp.server.db.model.resources import Worker
from pulp.server.exceptions import PulpCodedException, MissingResource
from pulp.server.webservices import serialization
from pulp.server.webservices.controllers import dispatch as dispatch_controller


class TestTaskResource(PulpWebservicesTests):
    """
    Test the TaskResource class.
    """
    def setUp(self):
        super(TestTaskResource, self).setUp()
        TaskStatus.get_collection().remove()
        self.task_resource = dispatch_controller.TaskResource()

    def tearDown(self):
        super(TestTaskResource, self).tearDown()
        TaskStatus.get_collection().remove()

    @mock.patch('pulp.server.async.tasks.controller.revoke', autospec=True)
    def test_DELETE_celery_task(self, revoke):
        """
        Test the DELETE() method with a UUID that does not correspond to a UUID that the
        coordinator is aware of. This should cause a revoke call to Celery's Controller.
        """
        task_id = '1234abcd'
        now = datetime.utcnow()
        test_worker = Worker('test_worker', now)
        TaskStatusManager.create_task_status(task_id, test_worker.name)

        self.task_resource.DELETE(task_id)

        revoke.assert_called_once_with(task_id, terminate=True)

    def test_DELETE_completed_celery_task(self):
        """
        Test the DELETE() method raises a TaskComplete exception if the task is already complete.
        """
        task_id = '1234abcd'
        now = datetime.utcnow()
        test_worker = Worker('test_worker', now)
        TaskStatusManager.create_task_status(task_id, test_worker.name,
                                             state=constants.CALL_FINISHED_STATE)
        self.assertRaises(PulpCodedException, self.task_resource.DELETE, task_id)

    def test_DELETE_non_existing_celery_task(self):
        """
        Test the DELETE() method raises a TaskNotFound exception if the task is not found.
        """
        task_id = '1234abcd'
        self.assertRaises(MissingResource, self.task_resource.DELETE, task_id)

    @mock.patch('pulp.server.async.tasks.controller.revoke', autospec=True)
    def test_DELETE_doesnt_cancel_spawned_celery_task(self, revoke):
        """
        Test the DELETE() which should cause a revoke call to Celery's Controller.
        This also tests that the spawned tasks are canceled as well.
        """
        task_id = '1234abcd'
        spawned_task_id = 'spawned_task'
        spawned_by_spawned_task_id = 'spawned_by_spawned_task'
        now = datetime.utcnow()
        test_worker = Worker('test_worker', now)
        TaskStatusManager.create_task_status(task_id, test_worker.queue_name)
        TaskStatusManager.create_task_status(spawned_task_id, test_worker.queue_name)
        TaskStatusManager.create_task_status(spawned_by_spawned_task_id, test_worker.queue_name)
        TaskStatusManager.update_task_status(task_id, delta={'spawned_tasks': [spawned_task_id]})
        TaskStatusManager.update_task_status(spawned_task_id,
                                             delta={'spawned_tasks': [spawned_by_spawned_task_id]})
        self.task_resource.DELETE(task_id)

        self.assertEqual(revoke.call_count, 1)
        revoke.assert_called_once_with(task_id, terminate=True)


class TestTaskCollection(base.PulpWebserviceTests):
    """
    Test the TaskCollection class.
    """
    def test_GET_celery_tasks(self):
        """
        Test the GET() method to get all current tasks.
        """
        # Populate a couple of task statuses
        task_id1 = str(uuid.uuid4())
        queue_1 = 'queue_1'
        state1 = 'waiting'

        task_id2 = str(uuid.uuid4())
        queue_2 = 'queue_2'
        state2 = 'running'
        tags = ['random', 'tags']

        TaskStatusManager.create_task_status(task_id1, queue_1, tags, state1)
        TaskStatusManager.create_task_status(task_id2, queue_2, tags, state2)
        status, body = self.get('/v2/tasks/')

        # Validate
        self.assertEqual(200, status)
        self.assertTrue(len(body) == 2)
        for task in body:
            if task['task_id'] == task_id1:
                self.assertEqual(task['_href'],
                                 serialization.dispatch.task_result_href(task)['_href'])
                self.assertEquals(task['state'], state1)
                self.assertEqual(task['queue'], queue_1)
            else:
                self.assertEqual(task['_href'],
                                 serialization.dispatch.task_result_href(task)['_href'])
                self.assertEquals(task['state'], state2)
                self.assertEqual(task['queue'], queue_2)
        self.assertEquals(task['tags'], tags)

    def test_GET_celery_tasks_by_tags(self):
        """
        Test the GET() method to get all current tasks.
        """
        # Populate a few of task statuses
        task_id1 = str(uuid.uuid4())
        queue_1 = 'queue_1'
        state1 = 'waiting'
        tags1 = ['random', 'tags']

        task_id2 = str(uuid.uuid4())
        queue_2 = 'queue_2'
        state2 = 'running'
        tags2 = ['random', 'tags']

        task_id3 = str(uuid.uuid4())
        queue_3 = 'queue_3'
        state3 = 'running'
        tags3 = ['random']

        TaskStatusManager.create_task_status(task_id1, queue_1, tags1, state1)
        TaskStatusManager.create_task_status(task_id2, queue_2, tags2, state2)
        TaskStatusManager.create_task_status(task_id3, queue_3, tags3, state3)

        # Validate for tags
        status, body = self.get('/v2/tasks/?tag=random&tag=tags')
        self.assertEqual(200, status)
        self.assertTrue(len(body) == 2)
        for task in body:
            if task['task_id'] == task_id1:
                self.assertEquals(task['state'], state1)
                self.assertEqual(task['queue'], queue_1)
                self.assertEqual(task['tags'], tags1)
            else:
                self.assertEqual(task['task_id'], task_id2)
                self.assertEquals(task['state'], state2)
                self.assertEqual(task['queue'], queue_2)
                self.assertEquals(task['tags'], tags2)

        # Negative test
        status, body = self.get('/v2/tasks/?tag=non_existent')
        self.assertEqual(200, status)
        self.assertTrue(len(body) == 0)

    def test_GET_celery_task_by_id(self):
        """
        Test the GET() method to get a current task with given id.
        """
        # Populate a couple of task statuses
        task_id1 = str(uuid.uuid4())
        queue_1 = 'queue_1'
        state1 = 'waiting'

        task_id2 = str(uuid.uuid4())
        queue_2 = 'queue_2'
        state2 = 'running'
        tags = ['random', 'tags']

        TaskStatusManager.create_task_status(task_id1, queue_1, tags, state1)
        TaskStatusManager.create_task_status(task_id2, queue_2, tags, state2)
        status, body = self.get('/v2/tasks/%s/' % task_id2)

        # Validate
        self.assertEqual(200, status)
        self.assertTrue(isinstance(body, dict))
        self.assertEquals(body['state'], state2)
        self.assertEqual(body['queue'], queue_2)
        self.assertEquals(body['tags'], tags)

    def test_GET_celery_task_by_missing_id(self):
        """
        Test the GET() method to get a current task with given id.
        """
        # Populate a couple of task statuses
        task_id1 = str(uuid.uuid4())
        queue_1 = 'queue_1'
        state1 = 'waiting'
        tags = ['random', 'tags']

        TaskStatusManager.create_task_status(task_id1, queue_1, tags, state1)
        non_existing_task_id = str(uuid.uuid4())
        status, body = self.get('/v2/tasks/%s/' % non_existing_task_id)

        # Validate
        self.assertEqual(404, status)
        self.assertTrue(isinstance(body, dict))
        self.assertTrue('Missing resource' in body['error_message'])
        self.assertTrue(non_existing_task_id in body['error_message'])


class SearchTaskCollectionTests(PulpWebservicesTests):

    def get_task(self):
        return {u'task_id': u'foo',
                u'spawned_tasks': [u'bar', u'baz']}

    @mock.patch('pulp.server.webservices.controllers.dispatch.SearchTaskCollection.'
                '_get_query_results_from_get', autospec=True)
    def test_get(self, mock_get_results):
        search_controller = dispatch_controller.SearchTaskCollection()
        mock_get_results.return_value = [self.get_task()]
        processed_tasks_json = search_controller.GET()

        # Mimic the processing
        updated_task = dispatch_controller.task_serializer(self.get_task())
        processed_tasks = json.loads(processed_tasks_json)
        compare_dict(updated_task, processed_tasks[0])

        #validate the permissions
        self.validate_auth(authorization.READ)

    @mock.patch('pulp.server.webservices.controllers.dispatch.SearchTaskCollection.'
                '_get_query_results_from_post', autospec=True)
    def test_post(self, mock_get_results):
        search_controller = dispatch_controller.SearchTaskCollection()
        mock_get_results.return_value = [self.get_task()]
        processed_tasks_json = search_controller.POST()

        # Mimic the processing
        updated_task = dispatch_controller.task_serializer(self.get_task())
        processed_tasks = json.loads(processed_tasks_json)
        compare_dict(updated_task, processed_tasks[0])

        #validate the permissions
        self.validate_auth(authorization.READ)
    #
    # @mock.patch('pulp.server.managers.factory.repo_distributor_manager')
    # @mock.patch('pulp.server.tasks.repository.distributor_delete', autospec=True)
    # def test_delete(self, mock_delete_task, mock_manager_factory):
    #     repo_distributor = repositories.RepoDistributor()
    #
    #     async_task = AsyncResult('foo-id')
    #     mock_delete_task.apply_async_with_reservation.return_value = async_task
    #     self.assertRaises(OperationPostponed, repo_distributor.DELETE,
    #                       "foo-repo", "foo-distributor")
    #     task_tags = ['pulp:repository:foo-repo',
    #                  'pulp:repository_distributor:foo-distributor',
    #                  'pulp:action:remove_distributor']
    #     mock_delete_task.apply_async_with_reservation.assert_called_once_with(
    #         tags.RESOURCE_REPOSITORY_TYPE, 'foo-repo',
    #         ['foo-repo', 'foo-distributor'], tags=task_tags)
    #
    #     #validate the permissions
    #     self.validate_auth(authorization.UPDATE)
    #
    #     try:
    #         repo_distributor.DELETE("foo-repo", "foo-distributor")
    #     except OperationPostponed, op:
    #         self.assertEquals(op.call_report, async_task)
    #
    # @mock.patch('pulp.server.managers.factory.repo_distributor_manager')
    # @mock.patch('pulp.server.tasks.repository.distributor_update', autospec=True)
    # def test_put(self, mock_update_task, mock_manager):
    #     repo_distributor = repositories.RepoDistributor()
    #     new_config = {'key': 'updated'}
    #     repo_distributor.params = mock.Mock(return_value={'distributor_config': new_config,
    #                                                       'delta': {}})
    #
    #     async_task = AsyncResult('foo-id')
    #     mock_update_task.apply_async_with_reservation.return_value = async_task
    #     self.assertRaises(OperationPostponed, repo_distributor.PUT, "foo-repo", "foo-distributor")
    #
    #     task_tags = ['pulp:repository:foo-repo',
    #                  'pulp:repository_distributor:foo-distributor',
    #                  'pulp:action:update_distributor']
    #     mock_update_task.apply_async_with_reservation.assert_called_once_with(
    #         tags.RESOURCE_REPOSITORY_TYPE, 'foo-repo',
    #         ['foo-repo', 'foo-distributor', new_config, {}], tags=task_tags)
    #
    #     #validate the permissions
    #     self.validate_auth(authorization.UPDATE)
    #
    #     try:
    #         repo_distributor.PUT("foo-repo", "foo-distributor")
    #     except OperationPostponed, op:
    #         self.assertEquals(op.call_report, async_task)
    #
    # @mock.patch('pulp.server.tasks.repository.distributor_update', autospec=True)
    # def test_put_missing_config_raises_exception(self, mock_update_task):
    #     repo_distributor = repositories.RepoDistributor()
    #     repo_distributor.params = mock.Mock(return_value={'distributor_config': None})
    #     self.assertRaises(MissingResource, repo_distributor.PUT, 'foo', 'bar')
