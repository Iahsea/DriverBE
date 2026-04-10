import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { App as AntdApp, Modal, Input } from 'antd'
import {
    listFriends,
    listFriendRequests,
    listFriendSuggestions,
    searchPeople,
    sendFriendRequest,
    acceptFriendRequest,
    rejectFriendRequest,
    deleteFriend,
} from '../api/friends.js'
import '../styles/FriendsPage.css'

function FriendsPage() {
    const { message } = AntdApp.useApp()
    const navigate = useNavigate()
    const [activeTab, setActiveTab] = useState('requests')
    const [requests, setRequests] = useState([])
    const [friends, setFriends] = useState([])
    const [loading, setLoading] = useState(false)
    const [suggestionsLoading, setSuggestionsLoading] = useState(false)
    const [suggestions, setSuggestions] = useState([])
    const [searchResults, setSearchResults] = useState([])
    const [search, setSearch] = useState('')
    const [modalOpen, setModalOpen] = useState(false)
    const [requestUserId, setRequestUserId] = useState('')

    async function fetchData() {
        setLoading(true)
        try {
            const requestData = await listFriendRequests()
            setRequests(requestData.requests || [])
            
            if (activeTab === 'friends') {
                const friendsData = await listFriends()
                setFriends(friendsData.friends || [])
            }
        } catch (error) {
            message.error(error.message || 'Failed to load data')
        } finally {
            setLoading(false)
        }
    }

    useEffect(() => {
        fetchData()
    }, [activeTab])

    useEffect(() => {
        let active = true
        async function fetchSuggestions() {
            setSuggestionsLoading(true)
            try {
                const data = await listFriendSuggestions(12)
                if (active) {
                    setSuggestions(data.suggestions || [])
                }
            } catch (error) {
                if (active) {
                    message.error(error.message || 'Failed to load suggestions')
                }
            } finally {
                if (active) {
                    setSuggestionsLoading(false)
                }
            }
        }
        fetchSuggestions()
        return () => {
            active = false
        }
    }, [message])

    useEffect(() => {
        const query = search.trim()
        if (!query) {
            setSearchResults([])
            return undefined
        }

        const timer = setTimeout(async () => {
            try {
                const data = await searchPeople(query, 20)
                setSearchResults(data.results || [])
            } catch (error) {
                message.error(error.message || 'Search failed')
            }
        }, 300)

        return () => clearTimeout(timer)
    }, [search, message])

    const filteredRequests = useMemo(() => {
        if (!search) {
            return requests
        }
        return requests.filter((request) =>
            request.from_username?.toLowerCase().includes(search.toLowerCase())
        )
    }, [requests, search])

    const filteredFriends = useMemo(() => {
        if (!search) {
            return friends
        }
        return friends.filter((friend) =>
            friend.username?.toLowerCase().includes(search.toLowerCase())
        )
    }, [friends, search])

    const peopleList = useMemo(() => {
        return search.trim() ? searchResults : suggestions
    }, [search, searchResults, suggestions])

    async function handleSendRequest() {
        if (!requestUserId) {
            message.warning('Enter user ID to invite')
            return
        }
        try {
            await sendFriendRequest(requestUserId)
            message.success('Friend request sent')
            setModalOpen(false)
            setRequestUserId('')
            fetchData()
        } catch (error) {
            message.error(error.message || 'Failed to send request')
        }
    }

    async function handleAccept(requestId) {
        try {
            await acceptFriendRequest(requestId)
            message.success('Request accepted')
            fetchData()
        } catch (error) {
            message.error(error.message || 'Failed to accept')
        }
    }

    async function handleReject(requestId) {
        try {
            await rejectFriendRequest(requestId)
            message.info('Request declined')
            fetchData()
        } catch (error) {
            message.error(error.message || 'Failed to decline')
        }
    }

    async function handleQuickAdd(userId) {
        try {
            await sendFriendRequest(userId)
            message.success('Friend request sent')
            fetchData()
        } catch (error) {
            message.error(error.message || 'Failed to send request')
        }
    }

    return (
        <div className="friends-page">
            <div className="friends-shell">
                <aside className="friends-rail">
                    <div>
                        <div className="rail-title">{activeTab === 'requests' ? 'Requests' : 'Friends'}</div>
                        <div className="rail-subtitle">
                            {activeTab === 'requests' ? 'Manage requests' : 'Your friends'}
                        </div>
                    </div>
                    <div className="rail-nav">
                        <button 
                            className={`rail-item ${activeTab === 'requests' ? 'active' : ''}`} 
                            type="button"
                            onClick={() => setActiveTab('requests')}
                        >
                            <span>💬</span>
                            Requests
                        </button>
                        <button 
                            className={`rail-item ${activeTab === 'friends' ? 'active' : ''}`} 
                            type="button"
                            onClick={() => setActiveTab('friends')}
                        >
                            <span>👥</span>
                            Friends
                        </button>
                    </div>
                    <button className="rail-cta" type="button" onClick={() => setModalOpen(true)}>
                        Invite Friends
                    </button>
                </aside>

                <main className="friends-main">
                    {activeTab === 'requests' && (
                        <>
                            <section className="friends-header">
                                <div className="friends-title-row">
                                    <h2 className="friends-title">Find People</h2>
                                    <div className="friends-search">
                                        <span className="search-icon">🔍</span>
                                        <input
                                            placeholder="Search by name or email..."
                                            value={search}
                                            onChange={(event) => setSearch(event.target.value)}
                                        />
                                    </div>
                                </div>
                            </section>

                            <section className="friends-section">
                                <div className="section-head">
                                    <h3>Pending Requests</h3>
                                    <span className="section-pill">{filteredRequests.length} New</span>
                                </div>
                                <div className="request-grid">
                                    {loading && <div className="empty-block">Loading requests...</div>}
                                    {!loading && filteredRequests.length === 0 && (
                                        <div className="empty-block">No pending requests.</div>
                                    )}
                                    {!loading &&
                                        filteredRequests.map((request) => (
                                            <div className="request-card" key={request.id}>
                                                <img
                                                    alt="Sender"
                                                    src={
                                                        request.avatar_url ||
                                                        'https://lh3.googleusercontent.com/aida-public/AB6AXuCg3YahN58Lk6blst1GdzL1mahkgqBVb1wclRew6d8XAMw9nOEuim7i_El400KLaYyhHdoMtvcrzUrvl0HOPANfDdn7qB80RYzUHDVjUkv2Kl3_1D2TYtf1ojMW0yXVRSnXUz-tl_ENv34rLoeU6HaiT7oZ36NlpVv61VjrCZRIG4vwz3Oqno7MujIK1fTx-YwgurMNka4xe9plmbpH5BvgyO9SbUtOzKj3tsOC9tMlKurB9M82Pu-vt4OOpEhv-kNXAkvlj1sC6PQ_'
                                                    }
                                                    style={{ cursor: 'pointer' }}
                                                    onClick={() => navigate(`/profile/${request.from_id}`)}
                                                />
                                                <div>
                                                    <h4>{request.from_username}</h4>
                                                    <p>Requested recently</p>
                                                    <div className="request-actions">
                                                        <button className="btn-primary" type="button" onClick={() => handleAccept(request.id)}>
                                                            Confirm
                                                        </button>
                                                        <button className="btn-ghost" type="button" onClick={() => handleReject(request.id)}>
                                                            Delete
                                                        </button>
                                                    </div>
                                                </div>
                                            </div>
                                        ))}
                                </div>
                            </section>

                            <section className="friends-section">
                                <div className="section-head">
                                    <h3>People You May Know</h3>
                                    <button className="btn-ghost" type="button">
                                        See All
                                    </button>
                                </div>
                                <div className="suggestion-grid">
                                    {suggestionsLoading && <div className="empty-block">Loading suggestions...</div>}
                                    {!suggestionsLoading && peopleList.length === 0 && (
                                        <div className="empty-block">
                                            {search.trim() ? 'No matches found.' : 'No suggestions yet.'}
                                        </div>
                                    )}
                                    {!suggestionsLoading &&
                                        peopleList.map((person) => (
                                            <div className="suggestion-card" key={person.id}>
                                                <img
                                                    alt={person.username}
                                                    src="https://lh3.googleusercontent.com/aida-public/AB6AXuAJPpyieHWeKg3tCwQ6pKSc2Omi0Epbg2_rWjgDH4lBnpTBrT6YkJd70XE_VuKCWkW223aZ5Uc-zqL8h5diH6Pz5acsu_pJrslS6X-JVgfq-1vE8bqJSq8EFsB0ozTI8wiPXGZ0QBybnXHEPYy6lZ2biB1H_UPO_f4hgqBqsZ3cvMmiUSPQlyZEZv84mlRYG4tJStEWlGuaGs0iqkfrboSF5u9Q2fV1UPOTmlTd19FVPaI7FLEVqlVj2yNDQm9ZAvRC1Wg46eEvBM6d"
                                                    style={{ cursor: 'pointer' }}
                                                    onClick={() => navigate(`/profile/${person.id}`)}
                                                />
                                                <div>
                                                    <h5>{person.username}</h5>
                                                    <p>
                                                        {person.mutual_count > 0
                                                            ? `${person.mutual_count} Mutual Friends`
                                                            : person.email}
                                                    </p>
                                                </div>
                                                <button className="btn-primary" type="button" onClick={() => handleQuickAdd(person.id)}>
                                                    Add
                                                </button>
                                            </div>
                                        ))}
                                </div>
                            </section>

                            <section className="friends-section">
                                <div className="banner-card">
                                    <img
                                        alt="Community"
                                        src="https://lh3.googleusercontent.com/aida-public/AB6AXuC1sRVKxnB8olqwBtASiDIeb-jr5-AKzB7BGwsnutBXkTKyw64ULTgfIw5QWdjLoJLYAQLsJ63yXDfnfvnALNw95qVj7nWpIi-iLJy7o5QuwnglDrdPErAwWBfn9zNUSeTPs31rvfV8unn26ExfzYogof66GwkhU7PYt_jpaNp1ON1nryx6THJnNAjQmqaPo_lqm92lJ6riHMGz-FK8z5HTzYSIHcth-EPv6lU2LjbAQGq7Bw3-cmHz24bOQ_sebSCfxYeDCrA_BJsi"
                                    />
                                    <div className="banner-overlay" />
                                    <div className="banner-content">
                                        <h4>Connect with more people</h4>
                                        <p>Sync your phone contacts to find friends and coworkers instantly on Messenger.</p>
                                        <button type="button">Sync Contacts</button>
                                    </div>
                                </div>
                            </section>
                        </>
                    )}

                    {activeTab === 'friends' && (
                        <>
                            <section className="friends-header">
                                <div className="friends-title-row">
                                    <h2 className="friends-title">My Friends</h2>
                                    <div className="friends-search">
                                        <span className="search-icon">🔍</span>
                                        <input
                                            placeholder="Search friends..."
                                            value={search}
                                            onChange={(event) => setSearch(event.target.value)}
                                        />
                                    </div>
                                </div>
                            </section>

                            <section className="friends-section">
                                <div className="section-head">
                                    <h3>Friends</h3>
                                    <span className="section-pill">{filteredFriends.length}</span>
                                </div>
                                <div className="suggestion-grid">
                                    {loading && <div className="empty-block">Loading friends...</div>}
                                    {!loading && filteredFriends.length === 0 && (
                                        <div className="empty-block">No friends yet.</div>
                                    )}
                                    {!loading &&
                                        filteredFriends.map((friend) => (
                                            <div className="suggestion-card" key={friend.id}>
                                                <img
                                                    alt={friend.username}
                                                    src="https://lh3.googleusercontent.com/aida-public/AB6AXuAJPpyieHWeKg3tCwQ6pKSc2Omi0Epbg2_rWjgDH4lBnpTBrT6YkJd70XE_VuKCWkW223aZ5Uc-zqL8h5diH6Pz5acsu_pJrslS6X-JVgfq-1vE8bqJSq8EFsB0ozTI8wiPXGZ0QBybnXHEPYy6lZ2biB1H_UPO_f4hgqBqsZ3cvMmiUSPQlyZEZv84mlRYG4tJStEWlGuaGs0iqkfrboSF5u9Q2fV1UPOTmlTd19FVPaI7FLEVqlVj2yNDQm9ZAvRC1Wg46eEvBM6d"
                                                    style={{ cursor: 'pointer' }}
                                                    onClick={() => navigate(`/profile/${friend.id}`)}
                                                />
                                                <div>
                                                    <h5>{friend.username}</h5>
                                                    <p>{friend.email || 'Friend'}</p>
                                                </div>
                                                <button 
                                                    className="btn-ghost" 
                                                    type="button" 
                                                    onClick={async () => {
                                                        try {
                                                            await deleteFriend(friend.id)
                                                            message.success('Friend removed')
                                                            fetchData()
                                                        } catch (error) {
                                                            message.error(error.message || 'Failed to remove')
                                                        }
                                                    }}
                                                >
                                                    Remove
                                                </button>
                                            </div>
                                        ))}
                                </div>
                            </section>
                        </>
                    )}
                </main>
            </div>

            <nav className="friends-bottom-nav">
                <div className={`bottom-item ${activeTab === 'requests' ? 'active' : ''}`} onClick={() => setActiveTab('requests')}>
                    💬 Requests
                </div>
                <div className={`bottom-item ${activeTab === 'friends' ? 'active' : ''}`} onClick={() => setActiveTab('friends')}>
                    👥 Friends
                </div>
            </nav>

            <Modal
                title="Add New Friend"
                open={modalOpen}
                onCancel={() => setModalOpen(false)}
                onOk={handleSendRequest}
                okText="Send Request"
            >
                <Input
                    placeholder="Paste friend user ID"
                    value={requestUserId}
                    onChange={(event) => setRequestUserId(event.target.value)}
                />
            </Modal>
        </div>
    )
}

export default FriendsPage
