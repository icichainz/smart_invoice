import React, { useState, useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { Button } from '../components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Alert, AlertDescription } from '../components/ui/alert';
import { Save, SaveAll } from 'lucide-react';
import { invoiceApi, clientApi } from '../services/api';
import { Invoice, Client, InvoiceItemCreate } from '../types';
import { formatDateForInput, getErrorMessage } from '../utils';

const InvoiceForm: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const isEditing = Boolean(id);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [clients, setClients] = useState<Client[]>([]);
  
  // Form state
  const [selectedClient, setSelectedClient] = useState<Client | null>(null);
  const [dueDate, setDueDate] = useState('');
  const [vatRate, setVatRate] = useState(0);
  const [items, setItems] = useState<InvoiceItemCreate[]>([]);

  useEffect(() => {
    loadClients();
    if (!isEditing) {
      addNewItem();
    }
  }, []);

  useEffect(() => {
    if (isEditing && id && clients.length > 0) {
      loadInvoice(parseInt(id));
    }
  }, [isEditing, id, clients]);

  const loadClients = async () => {
    try {
      const clientList = await clientApi.list();
      setClients(clientList);
    } catch (err) {
      setError(getErrorMessage(err));
    }
  };

  const loadInvoice = async (invoiceId: number) => {
    try {
      setLoading(true);
      const invoiceData = await invoiceApi.get(invoiceId);
      
      const client = clients.find(c => c.id === invoiceData.client);
      setSelectedClient(client || null);
      
      setDueDate(formatDateForInput(invoiceData.due_date));
      setVatRate(invoiceData.vat_rate);
      
      const formItems: InvoiceItemCreate[] = invoiceData.items
        .filter(item => item.is_active)
        .map(item => ({
          invoice: invoiceData.id,
          title: item.title,
          description: item.description,
          amount: item.amount,
          quantity: item.quantity,
        }));
      
      setItems(formItems.length > 0 ? formItems : [createNewItem()]);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  const createNewItem = (): InvoiceItemCreate => ({
    invoice: 0,
    title: '',
    description: '',
    amount: '0.00',
    quantity: 1,
  });

  const addNewItem = () => {
    setItems([...items, createNewItem()]);
  };

  const updateItem = (index: number, field: keyof InvoiceItemCreate, value: any) => {
    const updatedItems = [...items];
    updatedItems[index] = { ...updatedItems[index], [field]: value };
    setItems(updatedItems);
  };

  const removeItem = (index: number) => {
    if (items.length > 1) {
      setItems(items.filter((_, i) => i !== index));
    }
  };

  const calculateTotal = () => {
    const subtotal = items.reduce((sum, item) => {
      return sum + (parseFloat(item.amount) * item.quantity);
    }, 0);
    
    const vatAmount = subtotal * (vatRate / 100);
    const total = subtotal + vatAmount;
    
    return { subtotal, vatAmount, total };
  };

  const handleSave = async (saveAsDraft = false) => {
    try {
      setLoading(true);
      setError('');

      const invoiceData = {
        client: selectedClient?.id,
        due_date: dueDate || undefined,
        vat_rate: vatRate,
        status: 'unpaid' as const,
        save_as_draft: saveAsDraft,
        items: items.filter(item => item.title && item.amount),
      };

      if (isEditing && id) {
        await invoiceApi.update(parseInt(id), invoiceData);
      } else {
        await invoiceApi.create(invoiceData);
      }

      navigate('/invoices');
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  const { subtotal, vatAmount, total } = calculateTotal();

  if (loading && isEditing) {
    return (
      <div className="flex items-center justify-center min-h-64">
        <div className="text-muted-foreground">Loading...</div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold">
          {isEditing ? `Edit Invoice #${id}` : 'New Invoice'}
        </h1>
        <div className="space-x-2">
          <Button variant="outline" onClick={() => handleSave(true)} disabled={loading}>
            <SaveAll className="h-4 w-4 mr-2" />
            Save as Draft
          </Button>
          <Button onClick={() => handleSave(false)} disabled={loading}>
            <Save className="h-4 w-4 mr-2" />
            Save Invoice
          </Button>
        </div>
      </div>

      {error && (
        <Alert variant="destructive">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle>Invoice Details</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="client">Client</Label>
              <select
                id="client"
                value={selectedClient?.id || ''}
                onChange={(e) => {
                  const client = clients.find(c => c.id === parseInt(e.target.value));
                  setSelectedClient(client || null);
                }}
                className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
              >
                <option value="">Select a client</option>
                {clients.map((client) => (
                  <option key={client.id} value={client.id}>
                    {client.name}
                  </option>
                ))}
              </select>
            </div>
            
            <div className="space-y-2">
              <Label htmlFor="dueDate">Due Date</Label>
              <Input
                id="dueDate"
                type="date"
                value={dueDate}
                onChange={(e) => setDueDate(e.target.value)}
              />
            </div>
            
            <div className="space-y-2">
              <Label htmlFor="vatRate">VAT Rate (%)</Label>
              <Input
                id="vatRate"
                type="number"
                value={vatRate}
                onChange={(e) => setVatRate(parseFloat(e.target.value) || 0)}
                min="0"
                max="100"
                step="0.1"
              />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Invoice Summary</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex justify-between">
              <span>Subtotal:</span>
              <span>${subtotal.toFixed(2)}</span>
            </div>
            
            {vatRate > 0 && (
              <div className="flex justify-between">
                <span>VAT ({vatRate}%):</span>
                <span>${vatAmount.toFixed(2)}</span>
              </div>
            )}
            
            <div className="flex justify-between text-lg font-semibold border-t pt-2">
              <span>Total:</span>
              <span>${total.toFixed(2)}</span>
            </div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>Invoice Items</CardTitle>
            <Button variant="outline" onClick={addNewItem}>
              Add Item
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {items.map((item, index) => (
              <div key={index} className="border rounded-lg p-4 space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                  <div className="space-y-2">
                    <Label>Title</Label>
                    <Input
                      value={item.title}
                      onChange={(e) => updateItem(index, 'title', e.target.value)}
                      placeholder="Item title"
                    />
                  </div>
                  
                  <div className="space-y-2">
                    <Label>Description</Label>
                    <Input
                      value={item.description}
                      onChange={(e) => updateItem(index, 'description', e.target.value)}
                      placeholder="Item description"
                    />
                  </div>
                  
                  <div className="space-y-2">
                    <Label>Amount</Label>
                    <Input
                      type="number"
                      value={item.amount}
                      onChange={(e) => updateItem(index, 'amount', e.target.value)}
                      min="0"
                      step="0.01"
                    />
                  </div>
                  
                  <div className="space-y-2">
                    <Label>Quantity</Label>
                    <div className="flex items-center space-x-2">
                      <Input
                        type="number"
                        value={item.quantity}
                        onChange={(e) => updateItem(index, 'quantity', parseInt(e.target.value) || 1)}
                        min="1"
                        className="flex-1"
                      />
                      {items.length > 1 && (
                        <Button
                          variant="outline"
                          size="icon"
                          onClick={() => removeItem(index)}
                        >
                          ×
                        </Button>
                      )}
                    </div>
                  </div>
                </div>
                
                <div className="text-right text-sm text-muted-foreground">
                  Line Total: ${(parseFloat(item.amount) * item.quantity).toFixed(2)}
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default InvoiceForm;