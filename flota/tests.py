from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User, Group
from .models import ModeloVehiculo, Vehiculo, OrdenDeTrabajo, Repuesto, DetalleInsumoOT, MovimientoStock

class OrdenDeTrabajoCreationTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='testpassword')

        # Create group and add user to it
        group = Group.objects.create(name='Supervisor')
        self.user.groups.add(group)

        self.client.login(username='testuser', password='testpassword')

        self.modelo_vehiculo = ModeloVehiculo.objects.create(
            nombre='Test Model',
            marca='Test Brand',
            tipo='Camión'
        )
        self.vehiculo = Vehiculo.objects.create(
            numero_interno='123',
            patente='AB1234',
            modelo=self.modelo_vehiculo,
            kilometraje_actual=10000
        )

    def test_create_orden_de_trabajo(self):
        data = {
            'vehiculo': self.vehiculo.id,
            'tipo': 'CORRECTIVA',
            'sintomas_reportados': 'Test symptoms',
        }
        response = self.client.post(reverse('flota:ot_create'), data)

        # Check if the OT was created
        self.assertEqual(response.status_code, 302)
        self.assertTrue(OrdenDeTrabajo.objects.filter(vehiculo=self.vehiculo).exists())

class InventarioManagementTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='testpassword')
        group = Group.objects.create(name='Supervisor')
        self.user.groups.add(group)
        self.client.login(username='testuser', password='testpassword')

        self.modelo_vehiculo = ModeloVehiculo.objects.create(
            nombre='Test Model',
            marca='Test Brand',
            tipo='Camión'
        )
        self.vehiculo = Vehiculo.objects.create(
            numero_interno='123',
            patente='AB1234',
            modelo=self.modelo_vehiculo,
            kilometraje_actual=10000
        )
        self.ot = OrdenDeTrabajo.objects.create(
            vehiculo=self.vehiculo,
            tipo='CORRECTIVA',
            sintomas_reportados='Test symptoms'
        )
        self.repuesto = Repuesto.objects.create(
            nombre='Test Repuesto',
            numero_parte='12345',
            stock_actual=10
        )

    def test_add_repuesto_to_ot(self):
        # Add repuesto to OT
        DetalleInsumoOT.objects.create(
            orden_de_trabajo=self.ot,
            repuesto_inventario=self.repuesto,
            cantidad=2
        )

        # Create stock movement
        MovimientoStock.objects.create(
            repuesto=self.repuesto,
            tipo_movimiento='SALIDA_OT',
            cantidad=-2,
            orden_de_trabajo=self.ot,
            usuario_responsable=self.user
        )

        # Check if stock was updated
        self.repuesto.refresh_from_db()
        self.assertEqual(self.repuesto.stock_actual, 8)

class AuthenticationTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='testpassword')
        self.dashboard_url = reverse('flota:dashboard')

    def test_unauthenticated_user_cannot_access_dashboard(self):
        response = self.client.get(self.dashboard_url)
        self.assertNotEqual(response.status_code, 200)

    def test_authenticated_user_can_access_dashboard(self):
        self.client.login(username='testuser', password='testpassword')
        response = self.client.get(self.dashboard_url)
        self.assertEqual(response.status_code, 200)
